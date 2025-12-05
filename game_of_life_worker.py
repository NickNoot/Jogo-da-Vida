import socket
import sys
import numpy as np
import time

# Importa as funções de comunicação e as constantes de mensagem do módulo comum.
from common_utils import send_message, recv_message, MSG_TYPE_CHUNK, MSG_TYPE_UPDATE, MSG_TYPE_STOP

# Importa a classe sequencial para reutilizar a lógica de cálculo das regras do Jogo da Vida.
# O worker não precisa de uma grade completa, apenas da lógica para contar vizinhos e aplicar regras.
from game_of_life_sequential import GameOfLifeSequential 

class GameOfLifeWorker:
    """
    Implementa a lógica de um processo worker para o Jogo da Vida distribuído.
    O worker se conecta a um master, recebe um chunk da grade (com ghost cells),
    calcula a próxima geração para seu chunk principal e envia o resultado de volta.
    """
    def __init__(self, master_host: str, master_port: int):
        """
        Inicializa o worker, configurando a conexão com o master.

        Args:
            master_host (str): Endereço IP ou hostname do master.
            master_port (int): Porta na qual o master está escutando.
        """
        self.master_host = master_host
        self.master_port = master_port
        self.socket = None
        # Usamos uma instância de GameOfLifeSequential para reusar os métodos _count_live_neighbors e _apply_rules.
        # As dimensões iniciais (1,1) são placeholders e serão ajustadas dinamicamente para cada chunk recebido.
        self.gol_engine = GameOfLifeSequential(1, 1) 

    def connect_to_master(self):
        """Tenta estabelecer uma conexão TCP com o master."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.master_host, self.master_port))
            print(f"Worker conectado ao Master em {self.master_host}:{self.master_port}")
            return True
        except ConnectionRefusedError:
            print(f"Erro: Conexão recusada. O Master não está ativo ou o endereço/porta está incorreto.")
            return False
        except socket.timeout:
            print(f"Erro: Timeout ao tentar conectar ao Master em {self.master_host}:{self.master_port}.")
            return False
        except Exception as e:
            print(f"Erro inesperado ao conectar ao Master: {e}")
            return False

    def run(self):
        """
        Loop principal de execução do worker. 
        Recebe chunks, calcula a próxima geração e envia os resultados.
        """
        if not self.connect_to_master():
            return

        while True:
            try:
                # Recebe a mensagem do master. Bloqueia até que uma mensagem seja recebida.
                msg_type, data = recv_message(self.socket)

                if msg_type == MSG_TYPE_CHUNK:
                    # O master enviou um chunk para processar.
                    # 'data' é um dicionário contendo:
                    # 'chunk': a sub-grade principal que este worker deve calcular.
                    # 'top_ghost_row': a linha de vizinhos da parte de cima (da borda do chunk adjacente superior).
                    # 'bottom_ghost_row': a linha de vizinhos da parte de baixo (da borda do chunk adjacente inferior).
                    chunk = data['chunk']
                    top_ghost_row = data['top_ghost_row']
                    bottom_ghost_row = data['bottom_ghost_row']
                    
                    rows, cols = chunk.shape
                    
                    # Constrói uma grade temporária que inclui o chunk principal e as ghost cells.
                    # Esta grade é usada apenas para o cálculo local de vizinhos.
                    ghost_rows_count = 0
                    if top_ghost_row is not None:
                        ghost_rows_count += 1
                    if bottom_ghost_row is not None:
                        ghost_rows_count += 1
                    
                    # Ajusta as dimensões do motor GOL temporário do worker para a grade auxiliar.
                    self.gol_engine.rows = rows + ghost_rows_count
                    self.gol_engine.cols = cols
                    self.gol_engine.grid = np.zeros((self.gol_engine.rows, self.gol_engine.cols), dtype=int)

                    current_grid_row_idx = 0
                    # Preenche a linha fantasma superior, se existir.
                    if top_ghost_row is not None:
                        self.gol_engine.grid[current_grid_row_idx, :] = top_ghost_row
                        current_grid_row_idx += 1
                    
                    # Preenche o chunk principal.
                    self.gol_engine.grid[current_grid_row_idx : current_grid_row_idx + rows, :] = chunk
                    current_grid_row_idx += rows
                    
                    # Preenche a linha fantasma inferior, se existir.
                    if bottom_ghost_row is not None:
                        self.gol_engine.grid[current_grid_row_idx, :] = bottom_ghost_row
                    
                    # 'new_chunk_data' será o resultado, contendo apenas a parte correspondente ao chunk original.
                    new_chunk_data = np.zeros_like(chunk)

                    # Calcula a próxima geração APENAS para as linhas do chunk original.
                    # Os índices 'r_chunk' e 'c' referem-se ao chunk original.
                    for r_chunk in range(rows):
                        # 'r_effective' é o índice na 'self.gol_engine.grid' (que inclui ghost cells).
                        # Isso garante que as ghost cells sejam consideradas ao contar vizinhos.
                        r_effective = r_chunk
                        if top_ghost_row is not None: 
                            r_effective += 1 

                        for c in range(cols):
                            # Utiliza a lógica de GameOfLifeSequential para contar vizinhos e aplicar regras.
                            live_neighbors = self.gol_engine._count_live_neighbors(r_effective, c)
                            new_chunk_data[r_chunk, c] = self.gol_engine._apply_rules(chunk[r_chunk, c], live_neighbors)
                    
                    # Envia o chunk atualizado de volta para o master.
                    send_message(self.socket, MSG_TYPE_UPDATE, new_chunk_data)

                elif msg_type == MSG_TYPE_STOP:
                    # Master sinalizou para parar a execução.
                    print("Worker recebeu sinal de STOP. Encerrando.")
                    break
                elif msg_type is None and data is None:
                    # Conexão fechada graciosamente pelo master.
                    print("Master fechou a conexão. Encerrando worker.")
                    break
                else:
                    print(f"Worker recebeu tipo de mensagem desconhecido: {msg_type}")

            except (socket.error, RuntimeError) as e:
                print(f"Erro de comunicação do Worker: {e}. A conexão pode ter sido perdida. Encerrando.")
                break
            except pickle.UnpicklingError as e:
                print(f"Erro ao deserializar dados do Master: {e}. Os dados podem estar corrompidos. Encerrando.")
                break
            except Exception as e:
                print(f"Erro inesperado no Worker: {e}. Encerrando.")
                break

        self.socket.close() # Garante que o socket do worker seja fechado ao sair.
        print("Worker encerrado.")

# --- Configurações e Execução do Worker ---
if __name__ == "__main__":
    # O endereço e a porta do master devem ser passados como argumentos de linha de comando.
    # Ex: python game_of_life_worker.py 127.0.0.1 12345
    if len(sys.argv) != 3:
        print("Uso: python game_of_life_worker.py <MASTER_HOST> <MASTER_PORT>")
        sys.exit(1)

    MASTER_HOST = sys.argv[1]
    MASTER_PORT = int(sys.argv[2])

    worker = GameOfLifeWorker(MASTER_HOST, MASTER_PORT)
    worker.run()