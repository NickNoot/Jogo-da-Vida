import socket
import pickle
import struct
import numpy as np

# Constantes para definir os tipos de mensagem trocados entre master e worker.
# Cada tipo é uma sequência de 4 bytes (string de bytes) para identificação rápida.
MSG_TYPE_CHUNK = b'CHNK'   # O master envia um chunk de dados (sub-grade + ghost cells) para o worker.
MSG_TYPE_UPDATE = b'UPDT'  # O worker envia o chunk atualizado de volta para o master.
MSG_TYPE_STOP = b'STOP'    # O master sinaliza para o worker encerrar a execução.
MSG_TYPE_ACK = b'ACK '     # Um reconhecimento genérico, pode ser usado para confirmar recebimento (não usado na implementação atual, mas útil para extensões).

# O tamanho máximo de um bloco de dados a ser lido de uma vez do socket.
# Um valor razoável para a maioria das redes, equilibrando latência e overhead.
# Pode ser ajustado para otimização em redes específicas.
BUFFER_SIZE = 4096 

def send_message(sock: socket.socket, msg_type: bytes, data):
    """
    Empacota e envia um tipo de mensagem e dados serializados por um socket.
    O protocolo é: [4 bytes de tipo de mensagem] [4 bytes de tamanho dos dados] [dados serializados].
    Isso permite que o receptor saiba exatamente o que esperar e quanto ler.
    
    Args:
        sock (socket.socket): O objeto socket para enviar os dados.
        msg_type (bytes): O tipo de mensagem (deve ser uma string de bytes de 4 caracteres, e.g., b'CHNK').
        data: Os dados Python a serem serializados e enviados. Pode ser qualquer objeto serializável por pickle.
    
    Raises:
        socket.error: Se houver um problema na comunicação com o socket.
    """
    # Serializa os dados Python para uma sequência de bytes.
    # Pickle é flexível, mas pode ser lento para grandes volumes ou não seguro para dados de fontes não confiáveis.
    pickled_data = pickle.dumps(data)  
    
    # Empacota o tipo de mensagem e o comprimento dos dados em um cabeçalho de 8 bytes.
    # '!4sI' significa:
    #   ! : Network byte order (garante compatibilidade entre sistemas com diferentes ordens de bytes).
    #   4s: String de 4 bytes para o tipo de mensagem.
    #   I : Unsigned int de 4 bytes para o comprimento dos dados.
    header = struct.pack("!4sI", msg_type, len(pickled_data))
    
    # Envia o cabeçalho e os dados serializados em uma única operação, se possível, ou em partes.
    sock.sendall(header + pickled_data)

def recv_message(sock: socket.socket):
    """
    Recebe um tipo de mensagem e dados serializados de um socket e os deserializa.
    Lê o cabeçalho para determinar o tipo e o tamanho da mensagem, depois lê os dados.
    
    Args:
        sock (socket.socket): O objeto socket para receber os dados.
        
    Returns:
        tuple: (msg_type, data) - O tipo de mensagem (bytes) e os dados deserializados,
               ou (None, None) se a conexão foi fechada graciosamente pelo remetente.
        
    Raises:
        RuntimeError: Se a conexão for quebrada inesperadamente enquanto tenta ler o corpo da mensagem.
        pickle.UnpicklingError: Se os dados recebidos não puderem ser deserializados.
        socket.error: Se houver um problema na comunicação com o socket.
    """
    # Tenta receber o cabeçalho (8 bytes: 4 bytes para tipo + 4 bytes para tamanho).
    raw_header = b''
    while len(raw_header) < 8:
        # Lê em pedaços até completar o cabeçalho.
        packet = sock.recv(8 - len(raw_header))
        if not packet:
            # Conexão fechada antes de receber o cabeçalho completo.
            return None, None 
        raw_header += packet

    # Desempacota o cabeçalho para obter o tipo e o comprimento da mensagem.
    msg_type, msg_len = struct.unpack("!4sI", raw_header) 

    data_buffer = b''
    bytes_recd = 0
    # Loop para garantir que todos os bytes dos dados sejam recebidos, mesmo que em múltiplos pacotes.
    while bytes_recd < msg_len:
        # Recebe chunks de dados, o menor entre o restante a ler e o tamanho do buffer.
        chunk = sock.recv(min(msg_len - bytes_recd, BUFFER_SIZE))
        if not chunk:
            # Conexão quebrada no meio da leitura dos dados.
            raise RuntimeError("Socket connection broken: Incomplete data received.")
        data_buffer += chunk
        bytes_recd += len(chunk)
    
    # Deserializa os dados recebidos e os retorna junto com o tipo de mensagem.
    return msg_type, pickle.loads(data_buffer) 