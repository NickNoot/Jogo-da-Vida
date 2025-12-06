import socket
import threading
import numpy as np
import time
import os
from collections import deque # 'deque' é importado, mas não utilizado diretamente nesta versão. Pode ser útil para filas de mensagens ou buffers em implementações mais avançadas.

# Importa as funções de comunicação e as constantes de mensagem do módulo comum.
from common_utils import send_message, recv_message, MSG_TYPE_CHUNK, MSG_TYPE_UPDATE, MSG_TYPE_STOP

# Importa a classe sequencial para a base da grade e lógica principal (e.g., inicialização da grade, impressão).
from game_of_life_sequential import GameOfLifeSequential

# Porta padrão para o master escutar por conexões de workers.
DEFAULT_MASTER_PORT = 12345

class GameOfLifeDistributed(GameOfLifeSequential):
    """
    Implementa o processo Master para o Jogo da Vida distribuído.
    Herda de GameOfLifeSequential para gerenciar a grade principal e a lógica das regras
    (embora as regras sejam executadas pelos workers, o master detém o estado global).
    O Master é responsável por:
    1. Aceitar e gerenciar conexões de workers.
    2. Dividir a grade em "chunks" e distribuí-los aos workers.
    3. Coletar os resultados atualizados de cada worker.
    4. Reconstruir a grade global a partir dos chunks processados.
    5. Coordenar o ciclo de vida da simulação (início, gerações, parada).
    """
    def __init__(self, rows, cols, num_workers, initial_pattern=None, master_port=DEFAULT_MASTER_PORT):
        """
        Inicializa o master.

        Args:
            rows (int): Número de linhas da grade.
            cols (int): Número de colunas da grade.
            num_workers (int): Número esperado de workers.
            initial_pattern (str, optional): Padrão inicial da grade. Defaults to None.
            master_port (int): Porta para o master escutar por conexões de workers.
        
        Raises:
            ValueError: Se num_workers for inválido ou se a grade for muito pequena para os workers.
        """
        super().__init__(rows, cols, initial_pattern)
        if not (isinstance(num_workers, int) and num_workers > 0):
            raise ValueError("num_workers deve ser um inteiro positivo.")
        self.num_workers = num_workers
        self.master_port = master_port
        # O host '0.0.0.0' significa que o servidor escutará em todas as interfaces de rede disponíveis.
        # Isso é crucial para permitir que workers em máquinas diferentes (ou na mesma máquina com IPs diferentes)
        # possam se conectar ao master. Se fosse '127.0.0.1' (localhost), apenas conexões da própria máquina seriam aceitas.
        self.host = '0.0.0.0' 
        self.worker_sockets = [] # Lista para armazenar os objetos socket conectados de cada worker.
        self.worker_addresses = [] # Lista para armazenar os endereços IP/porta de cada worker conectado.
        self.worker_threads = [] # Lista de threads dedicadas para lidar com a comunicação assíncrona de cada worker.
        
        # Estrutura para armazenar os resultados atualizados de cada worker para a geração atual.
        # Inicialmente preenchida com None, indicando que nenhum resultado foi recebido ainda para a geração atual.
        self.current_generation_results = [None] * self.num_workers
        # Um Lock é uma primitiva de sincronização essencial para proteger recursos compartilhados (como 'current_generation_results')
        # de condições de corrida quando acessados por múltiplas threads simultaneamente.
        self.results_lock = threading.Lock() 
        # Uma Condition variable permite que threads esperem por uma condição específica (e.g., todos os resultados recebidos)
        # e sejam notificadas quando essa condição for satisfeita. É sempre associada a um Lock.
        self.results_condition = threading.Condition(self.results_lock) 

        # Calcula quantas linhas cada worker será responsável. A divisão pode não ser exata,
        # então o último worker pode receber um número ligeiramente maior de linhas.
        self.rows_per_worker = self.rows // self.num_workers
        if self.rows_per_worker == 0:
            raise ValueError(f"O número de linhas ({rows}) é menor que o número de workers ({num_workers}). "
                             "Cada worker deve receber pelo menos uma linha para processar.")
        
        # Verifica se o número de linhas é muito pequeno para garantir que cada worker receba pelo menos 1 linha
        if self.rows < self.num_workers:
             raise ValueError(f"O número de linhas da grade ({self.rows}) deve ser no mínimo igual ao número de workers ({self.num_workers}).")


        # Evento para sinalizar o encerramento do servidor e de todas as threads de forma coordenada.
        self.stop_server_event = threading.Event() 
        self.server_socket = None # O socket principal do servidor, usado para aceitar novas conexões.

    def _handle_worker_connection(self, worker_socket: socket.socket, worker_id: int):
        """
        Função executada por uma thread separada para lidar com a comunicação com um worker específico.
        Esta thread é responsável por receber mensagens do worker e processá-las.
        """
        try:
            print(f"Thread do Worker {worker_id} iniciada para {self.worker_addresses[worker_id]}.")
            # Loop de escuta contínuo até que o evento de parada do servidor seja ativado.
            while not self.stop_server_event.is_set():
                msg_type, data = recv_message(worker_socket)

                if msg_type == MSG_TYPE_UPDATE:
                    # O worker enviou o chunk atualizado após o processamento de uma geração.
                    with self.results_lock: # Adquire o lock para garantir acesso seguro à lista compartilhada.
                        self.current_generation_results[worker_id] = data
                        # Verifica se todos os workers já enviaram seus resultados para a geração atual.
                        if all(res is not None for res in self.current_generation_results):
                            # Se todos os resultados foram recebidos, notifica as threads que estão esperando
                            # na 'results_condition' (especificamente a thread principal da simulação).
                            self.results_condition.notify_all() 
                elif msg_type == MSG_TYPE_STOP or (msg_type is None and data is None):
                    # O worker parou (sinalizado pelo master ou a conexão foi fechada inesperadamente).
                    print(f"Worker {worker_id} desconectado ou sinalizou STOP. Endereço: {self.worker_addresses[worker_id]}.")
                    # Em um sistema distribuído mais robusto, a falha de um worker exigiria:
                    # 1. Detecção de falha (e.g., heartbeat, timeout).
                    # 2. Reatribuição do trabalho do worker falho para outro worker ou para o master.
                    # 3. Gerenciamento de estado para garantir a consistência.
                    break # Sai do loop, encerrando a thread do worker.
                else:
                    print(f"Worker {worker_id} recebeu tipo de mensagem desconhecido: {msg_type}")

        except (socket.error, RuntimeError) as e:
            # Captura erros de rede ou de tempo de execução.
            # Evita imprimir erros se o servidor já estiver em processo de desligamento, pois seriam esperados.
            if not self.stop_server_event.is_set(): 
                print(f"Erro na comunicação com Worker {worker_id} ({self.worker_addresses[worker_id]}): {e}. Thread encerrada.")
        except Exception as e:
            # Captura quaisquer outras exceções inesperadas.
            print(f"Erro inesperado na thread do Worker {worker_id} ({self.worker_addresses[worker_id]}): {e}. Thread encerrada.")
        finally:
            # Garante que o socket do worker seja fechado, liberando recursos do sistema operacional.
            worker_socket.close() 
            print(f"Thread do Worker {worker_id} encerrada.")

    def _start_server(self):
        """
        Inicia o servidor master para aceitar conexões de workers. 
        Este método é executado em uma thread separada para não bloquear a simulação principal
        enquanto aguarda as conexões dos workers.
        """
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # SO_REUSEADDR permite que o socket seja reutilizado imediatamente após o fechamento,
        # o que é muito útil durante o desenvolvimento e testes, pois evita o erro "Address already in use".
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
        try:
            self.server_socket.bind((self.host, self.master_port))
        except socket.error as e:
            print(f"Erro ao vincular o socket do master à porta {self.master_port}: {e}")
            self.stop_server_event.set() # Sinaliza falha crítica.
            return

        # O listen backlog (neste caso, self.num_workers) define o número máximo de conexões pendentes
        # que o sistema operacional pode enfileirar antes de recusar novas conexões.
        self.server_socket.listen(self.num_workers) 
        print(f"Master escutando em {self.host}:{self.master_port} para {self.num_workers} workers...")

        # Loop para aceitar o número esperado de workers.
        for i in range(self.num_workers):
            if self.stop_server_event.is_set(): # Verifica se deve parar antes de aceitar mais.
                print("Servidor Master encerrando antes de conectar todos os workers.")
                break
            try:
                # accept() é um método bloqueante que aguarda uma nova conexão de cliente.
                conn, addr = self.server_socket.accept() 
                self.worker_sockets.append(conn)
                self.worker_addresses.append(addr)
                print(f"Worker {i} conectado de {addr}")
                
                # Inicia uma thread para lidar com a comunicação com este worker específico.
                worker_thread = threading.Thread(target=self._handle_worker_connection, args=(conn, i))
                # daemon=True permite que o programa principal (Master) termine mesmo que esta thread
                # ainda esteja em execução. É útil para threads de background que não precisam ser
                # explicitamente encerradas antes da saída do programa.
                worker_thread.daemon = True 
                self.worker_threads.append(worker_thread)
                worker_thread.start()
            except socket.timeout:
                # Um timeout pode ser definido no socket do servidor (e.g., self.server_socket.settimeout(X)).
                # Se ocorrer, o accept() levantaria esta exceção em vez de bloquear indefinidamente.
                print("Timeout ao aceitar conexão de worker.")
                continue 
            except Exception as e:
                print(f"Erro ao aceitar conexão de worker: {e}")
                self.stop_server_event.set() # Sinaliza para parar tudo em caso de erro grave.
                break # Sai do loop de aceitação.

        if len(self.worker_sockets) != self.num_workers:
            print(f"Aviso: Apenas {len(self.worker_sockets)} de {self.num_workers} workers se conectaram. A simulação pode não funcionar corretamente.")
            if not self.stop_server_event.is_set(): 
                print("Encerrando Master devido a número insuficiente de workers ou erro de conexão.")
                self.stop_server_event.set()
                return False # Indica falha na inicialização.
        return True # Indica sucesso na inicialização.

    def _distribute_and_collect(self):
        """
        Distribui os chunks de grade para os workers, aguarda os resultados de todos eles e reconstrói a grade completa.
        Este é o coração da lógica de paralelização distribuída para cada geração.
        """
        # Limpa os resultados da geração anterior para a nova rodada, redefinindo-os para None.
        with self.results_lock:
            self.current_generation_results = [None] * self.num_workers
        
        # new_grid_parts = [None] * self.num_workers # Esta linha é redundante, pois current_generation_results será usado.

        # Distribui os chunks para cada worker
        for i in range(self.num_workers):
            # Define o intervalo de linhas (chunk) que este worker 'i' será responsável.
            start_row = i * self.rows_per_worker
            end_row = (i + 1) * self.rows_per_worker
            # O último worker pega as linhas restantes para garantir que todas as linhas da grade sejam cobertas.
            if i == self.num_workers - 1:
                end_row = self.rows
            
            # Extrai o chunk principal da grade para este worker.
            chunk = self.grid[start_row:end_row, :]

            # Prepara as "células fantasmas" (ghost cells) para as bordas do chunk.
            # As ghost cells são linhas extras que um worker precisa para calcular corretamente
            # o estado das células em suas próprias bordas, pois elas dependem de vizinhos
            # que estão no chunk de outro worker (ou nas bordas opostas da grade em um toroide).
            top_ghost_row = None
            bottom_ghost_row = None

            # Linha fantasma superior: é a linha imediatamente anterior ao 'start_row' do chunk.
            # Se o chunk for o primeiro (i=0), a ghost row superior vem do final da grade (condição toroidal).
            if start_row == 0:
                top_ghost_row = self.grid[self.rows - 1, :] # Última linha da grade
            else:
                top_ghost_row = self.grid[start_row - 1, :]

            # Linha fantasma inferior: é a linha imediatamente posterior ao 'end_row-1' do chunk.
            # Se o chunk for o último, a ghost row inferior vem do início da grade (condição toroidal).
            if end_row == self.rows:
                bottom_ghost_row = self.grid[0, :] # Primeira linha da grade
            else:
                bottom_ghost_row = self.grid[end_row, :]

            # Empacota os dados (chunk e ghost cells) para enviar ao worker.
            worker_data = {
                'chunk': chunk,
                'top_ghost_row': top_ghost_row,
                'bottom_ghost_row': bottom_ghost_row
            }
            
            # Envia o chunk e as ghost cells para o worker correspondente.
            # Esta operação é bloqueante até que a mensagem seja enviada.
            send_message(self.worker_sockets[i], MSG_TYPE_CHUNK, worker_data)

        # Espera por todos os resultados dos workers.
        with self.results_lock:
            # A thread principal da simulação aguarda aqui até que a 'results_condition' seja notificada.
            # Isso ocorre quando a última thread de worker a enviar seu resultado atualiza 'current_generation_results'
            # e verifica que todos os resultados estão presentes.
            self.results_condition.wait_for(lambda: all(res is not None for res in self.current_generation_results))
            # Cria uma cópia dos resultados para evitar modificações enquanto a reconstrução ocorre.
            new_grid_parts = self.current_generation_results[:] 

        # Reconstrói a nova grade completa a partir das partes recebidas de cada worker.
        # np.concatenate empilha os arrays NumPy verticalmente (ao longo do eixo 0),
        # formando a grade completa da próxima geração.
        self.grid = np.concatenate(new_grid_parts, axis=0)


    def update(self):
        """
        Sobreescreve o método update da classe base para distribuir o cálculo
        de uma nova geração entre os workers conectados.
        """
        if self.stop_server_event.is_set(): # Não tenta distribuir se o servidor já está encerrando.
            return
        
        self._distribute_and_collect() # Realiza a distribuição das tarefas e coleta dos resultados.

    def run_simulation(self, num_generations, visualize=False, clear_screen=True):
        """
        Executa a simulação distribuída por um número especificado de gerações.
        """
        if visualize and (self.rows > 40 or self.cols > 80):
            print("Aviso: A visualização pode ser muito lenta ou distorcida para grades grandes. Desativando visualização.")
            visualize = False

        print(f"Iniciando Master em {self.host}:{self.master_port}, aguardando {self.num_workers} workers...")
        
        # Inicia o servidor master em uma thread separada para aceitar conexões.
        # Isso permite que a thread principal continue com a lógica de simulação
        # enquanto o servidor aguarda conexões em background.
        server_thread = threading.Thread(target=self._start_server)
        server_thread.daemon = True # Permite que o programa principal termine mesmo que esta thread esteja ativa.
        server_thread.start()
        
        # Espera um breve momento para o servidor iniciar e para os workers terem tempo de conectar.
        # Em um ambiente de produção, um mecanismo de handshake mais robusto (e.g., um worker envia uma mensagem
        # de "pronto" e o master espera por N mensagens) seria preferível para garantir que todos os workers
        # estejam realmente conectados antes de prosseguir.
        time.sleep(2) 
        
        # Verifica se o número esperado de workers se conectou dentro do tempo limite.
        if len(self.worker_sockets) < self.num_workers:
            print("Erro: Não foi possível conectar o número esperado de workers. Encerrando simulação.")
            self.shutdown() # Garante que quaisquer workers conectados sejam desligados.
            return 0.0 # Retorna 0.0 para indicar falha ou não execução completa.

        print(f"Simulação DISTRIBUÍDA para grade {self.rows}x{self.cols} com {num_generations} gerações e {self.num_workers} workers...")
        start_time = time.perf_counter()

        for gen in range(num_generations):
            if self.stop_server_event.is_set():
                print(f"Simulação interrompida na geração {gen+1}.")
                break
            
            if visualize:
                # Limpa o console para uma visualização mais fluida.
                # 'cls' é para Windows, 'clear' para sistemas baseados em Unix (Linux, macOS).
                os.system('cls' if os.name == 'nt' else 'clear')
                print(f"Geração: {gen+1}/{num_generations}")
                self.print_grid()
                time.sleep(0.05) # Pequena pausa para tornar a visualização perceptível.
            self.update() # Chama o método de atualização distribuída.

        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        print(f"\nSimulação distribuída concluída para {num_generations} gerações.")
        print(f"Tempo de execução: {elapsed_time:.4f} segundos")
        
        self.shutdown() # Garante que todos os workers sejam parados e sockets fechados.
        return elapsed_time

    def shutdown(self):
        """
        Envia um sinal de parada para todos os workers conectados e fecha todos os sockets
        e threads de forma controlada.
        """
        print("Master: Enviando sinal de STOP para workers e encerrando.")
        self.stop_server_event.set() # Sinaliza para as threads de comunicação pararem seus loops.
        
        # Envia o sinal de parada para cada worker e fecha seus sockets.
        for i, sock in enumerate(self.worker_sockets):
            try:
                send_message(sock, MSG_TYPE_STOP, None) # Envia a mensagem de parada.
                # shutdown() desabilita a leitura e/ou escrita no socket. SHUT_RDWR desabilita ambos,
                # garantindo que nenhum dado adicional seja enviado ou recebido.
                sock.shutdown(socket.SHUT_RDWR) 
                sock.close() # Fecha o socket, liberando o recurso.
            except socket.error as e:
                print(f"Erro ao fechar socket do worker {i}: {e}")
        
        # Fecha o socket do servidor principal.
        if self.server_socket:
            try:   
                self.server_socket.close()
            except socket.error as e:
                print(f"Erro ao fechar server socket: {e}")
        
        # Tenta juntar as threads de comunicação dos workers para garantir que terminem.
        # O join() com timeout evita que o programa principal fique bloqueado indefinidamente
        # se uma thread não responder.
        for thread in self.worker_threads:
            if thread.is_alive():
                thread.join(timeout=1) # Dá um tempo para a thread terminar.
                if thread.is_alive():
                    print(f"Aviso: Thread worker ainda ativa após shutdown. Pode indicar que não respondeu ao STOP.")
        print("Master desligado.")


# --- Exemplo de Uso para Teste Rápido (Somente Master) ---
if __name__ == "__main__":
    # IMPORTANTE: Para testar esta parte, você precisará iniciar processos worker separadamente.
    # Ex: Abrir 3 terminais e em cada um executar: python game_of_life_worker.py 127.0.0.1 12345
    # Ou usar o script de comparação (compare_game_of_life.py) que fará isso automaticamente e de forma mais robusta.
    
    print("--- Teste Rápido da Versão DISTRIBUÍDA (MASTER) ---")
    
    # --- Configurações da Simulação ---
    GRID_ROWS = 200      # Número de linhas da grade
    GRID_COLS = 200      # Número de colunas da grade
    NUM_GENERATIONS = 50 # Número de gerações a simular
    INITIAL_PATTERN = 'random' 
    NUM_WORKERS = 2      # Número de workers que você espera conectar.
    MASTER_PORT = DEFAULT_MASTER_PORT
    VISUALIZE_SMALL_GRID = False # Para benchmarking, deve ser False.

    try:
        distributed_game = GameOfLifeDistributed(GRID_ROWS, GRID_COLS, NUM_WORKERS, initial_pattern=INITIAL_PATTERN, master_port=MASTER_PORT)
        
        # Esta parte aqui AGUARDARÁ que os workers se conectem.
        # Você precisa iniciar os workers em terminais separados antes de executar este script.
        # A simulação só começará quando o número esperado de workers estiver conectado.
        time_dist = distributed_game.run_simulation(NUM_GENERATIONS, visualize=VISUALIZE_SMALL_GRID)
        
        print(f"Tempo da simulação distribuída (Master): {time_dist:.4f} segundos.")
        
    except ValueError as e:
        print(f"Erro na configuração da simulação distribuída: {e}")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")
    finally:
        # Garante que o master seja desligado mesmo em caso de erro.
        if 'distributed_game' in locals() and distributed_game.server_socket:

            distributed_game.shutdown()
