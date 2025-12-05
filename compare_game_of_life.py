import time
import os
import sys # Importa sys para verificar a versão do Python ou outras configurações

# Importa as classes de seus respectivos arquivos
# Certifique-se de que esses arquivos (game_of_life_sequential.py e game_of_life_parallel_threads.py)
# estejam no mesmo diretório ou no PYTHONPATH.
from game_of_life_sequential import GameOfLifeSequential
from game_of_life_parallel_threads import GameOfLifeParallelThreads

if __name__ == "__main__":
    # --- Configurações da Simulação para Comparação ---
    # Para uma comparação significativa e para que o paralelismo possa demonstrar seu potencial,
    # é crucial usar grades maiores e um número substancial de gerações.
    # Grades muito pequenas ou poucas gerações podem fazer com que o overhead de inicialização
    # e coordenação de threads supere qualquer ganho de desempenho.
    
    GRID_ROWS = 1000     # Número de linhas da grade. Grades 1000x1000 ou maiores são ideais
    GRID_COLS = 1000     # Número de colunas da grade. para observar o impacto do paralelismo.
                         # Cuidado: grades muito grandes podem consumir muita memória (MemoryError).
    NUM_GENERATIONS = 100 # Número de gerações a simular. Um número maior amplifica a diferença de tempo.
    
    # Padrão inicial para a grade:
    # 'random': Preenche a grade com células vivas aleatoriamente. Bom para testar o desempenho geral
    #           e observar o comportamento emergente do Jogo da Vida em larga escala.
    # 'glider': Um padrão pequeno e conhecido que se move pela grade. Útil para depuração e
    #           verificação de corretude em grades menores, mas menos relevante para benchmarking.
    # None: Inicializa a grade vazia.
    INITIAL_PATTERN = 'random' 
    
    # Número de threads para a versão paralela.
    # os.cpu_count(): Retorna o número de CPUs no sistema (ou núcleos lógicos se hyperthreading estiver ativo).
    #                 É uma boa prática começar com este valor, pois geralmente maximiza o uso de recursos.
    #                 Experimente com valores como 1 (para baseline de thread), 2, 4, 8 para ver como o desempenho escala.
    #                 Para tarefas CPU-bound em Python, mais threads do que núcleos lógicos raramente trazem benefícios
    #                 e podem até degradar o desempenho devido ao overhead de troca de contexto e contenção do GIL.
    NUM_THREADS = os.cpu_count() 
    
    # Visualização: SEMPRE DEVE SER FALSE para medições de desempenho precisas!
    # Imprimir a grade no console (ou qualquer operação de I/O) adiciona um overhead significativo,
    # distorcendo os resultados de tempo de CPU. A visualização é útil para verificar a corretude,
    # mas não para benchmarking.
    VISUALIZE = False 

    # --- Execução da Versão SEQUENCIAL ---
    print("\n" + "="*70)
    print("Iniciando Comparação: Versão SEQUENCIAL")
    print("="*70)
    time_seq = None
    try:
        # Instancia a simulação sequencial.
        # É crucial que ambas as simulações (sequencial e paralela) comecem com o mesmo estado inicial
        # para uma comparação justa e significativa dos tempos de execução.
        game_seq = GameOfLifeSequential(GRID_ROWS, GRID_COLS, initial_pattern=INITIAL_PATTERN)
        print(f"Simulando {NUM_GENERATIONS} gerações para uma grade {GRID_ROWS}x{GRID_COLS} (sequencial)...")
        time_seq = game_seq.run_simulation(NUM_GENERATIONS, visualize=VISUALIZE)
        print(f"Tempo de execução sequencial: {time_seq:.4f} segundos.")
    except ValueError as e:
        print(f"Erro na configuração da simulação sequencial: {e}")
        print("Verifique os parâmetros como 'initial_pattern' ou dimensões da grade.")
    except MemoryError:
        print(f"Erro de memória ao alocar grade {GRID_ROWS}x{GRID_COLS}.")
        print("Tente reduzir as dimensões da grade (GRID_ROWS, GRID_COLS) ou o número de gerações.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado na simulação sequencial: {e}")
    print("="*70 + "\n")

    # --- Execução da Versão PARALELA com THREADS ---
    print("\n" + "="*70)
    print("Iniciando Comparação: Versão PARALELA com THREADS")
    print("="*70)
    time_par = None
    try:
        # Instancia a simulação paralela.
        # A grade é recriada com o mesmo padrão inicial para garantir condições de teste idênticas.
        game_par = GameOfLifeParallelThreads(GRID_ROWS, GRID_COLS, num_threads=NUM_THREADS, initial_pattern=INITIAL_PATTERN)
        print(f"Simulando {NUM_GENERATIONS} gerações para uma grade {GRID_ROWS}x{GRID_COLS} com {NUM_THREADS} threads (paralelo)...")
        time_par = game_par.run_simulation(NUM_GENERATIONS, visualize=VISUALIZE)
        print(f"Tempo de execução paralelo: {time_par:.4f} segundos.")
    except ValueError as e:
        print(f"Erro na configuração da simulação paralela: {e}")
        print("Verifique os parâmetros como 'initial_pattern', dimensões da grade ou 'num_threads'.")
    except MemoryError:
        print(f"Erro de memória ao alocar grade {GRID_ROWS}x{GRID_COLS}.")
        print("Tente reduzir as dimensões da grade (GRID_ROWS, GRID_COLS) ou o número de gerações.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado na simulação paralela: {e}")
    print("="*70 + "\n")

    # --- Resumo da Comparação ---
    if time_seq is not None and time_par is not None:
        print("\n" + "="*70)
        print("--- RELATÓRIO DE COMPARAÇÃO ---")
        print("="*70)
        print(f"Configuração da Simulação:")
        print(f"  Grade: {GRID_ROWS}x{GRID_COLS}")
        print(f"  Gerações: {NUM_GENERATIONS}")
        print(f"  Padrão Inicial: '{INITIAL_PATTERN}'")
        print(f"  Número de Threads Utilizadas: {NUM_THREADS} (de {os.cpu_count()} núcleos lógicos disponíveis)")
        print(f"\nResultados de Tempo:")
        print(f"  Tempo Sequencial: {time_seq:.4f} segundos")
        print(f"  Tempo Paralelo (Threads): {time_par:.4f} segundos")
        
        if time_par > 0: # Evita divisão por zero
            speedup = time_seq / time_par
            print(f"  Speedup (Tempo Sequencial / Tempo Paralelo): {speedup:.2f}x")
            
            # Interpretação do Speedup
            if speedup > 1.1: # Considera um ganho de 10% como "visível"
                print("\nConclusão: A versão paralela com threads foi visivelmente mais rápida.")
                print("Isso pode ocorrer se a implementação usar bibliotecas que liberam o GIL (ex: NumPy) ou se a tarefa tiver componentes I/O-bound.")
            elif speedup < 0.9: # Considera uma perda de 10% como "visível"
                print("\nConclusão: A versão sequencial foi mais rápida.")
                print("Este é um resultado comum para tarefas CPU-bound em Python devido ao Global Interpreter Lock (GIL).")
            else:
                print("\nConclusão: Ambas as versões tiveram desempenho similar, ou o ganho de paralelismo foi marginal.")
                print("O overhead de gerenciamento de threads pode ter anulado os benefícios do paralelismo.")
        else:
            print("\nNão foi possível calcular o speedup (o tempo paralelo registrado foi zero ou negativo).")

        print("\n--- Nota Importante sobre o Python e Threads (GIL) ---")
        print("O Python possui um mecanismo chamado Global Interpreter Lock (GIL).")
        print("O GIL é um mutex que protege o acesso aos objetos internos do interpretador Python,")
        print("garantindo que apenas uma thread Python execute bytecode Python por vez.")
        print("Para tarefas intensivas de CPU (CPU-bound), como esta simulação do Jogo da Vida,")
        print("o GIL impede o paralelismo real de execução em threads Python, mesmo em sistemas com múltiplos núcleos.")
        print("Mesmo com múltiplas threads, o interpretador só pode executar uma por vez, levando a um overhead de troca de contexto")
        print("entre as threads. Este overhead pode, em muitos casos, tornar a versão paralela com threads mais lenta que a sequencial.")
        print("O GIL é liberado automaticamente por certas operações de I/O ou por extensões C (como as do NumPy) que são")
        print("explicitamente projetadas para liberar o GIL durante suas operações intensivas, permitindo que outras threads Python")
        print("executem enquanto a extensão C está trabalhando. No entanto, a lógica central do Jogo da Vida (cálculo de vizinhos, aplicação de regras)")
        print("é predominantemente implementada em Python puro, onde o GIL atua.")
        print("\nPara obter paralelismo real e ganhos de desempenho substanciais em tarefas CPU-bound em Python, o módulo 'multiprocessing'")
        print("é geralmente a solução preferida. Ele usa processos separados, cada um com seu próprio interpretador Python e, portanto, seu próprio GIL,")
        print("permitindo a execução paralela em múltiplos núcleos de CPU. Embora 'multiprocessing' introduza seu próprio overhead (como comunicação entre processos - IPC),")
        print("ele é a abordagem mais eficaz para paralelismo CPU-bound em Python.")
        print("A implementação usando 'multiprocessing' seria o próximo passo lógico para alcançar ganhos de desempenho mais substanciais para este tipo de problema.")
        print("="*70)
import time
import os
import sys
import subprocess # Módulo para criar e gerenciar processos externos, essencial para a versão distribuída.
import signal     # Para enviar sinais de término a processos, crucial para o gerenciamento gracioso de workers.

# Importa as classes das suas respectivas implementações
# Certifique-se de que esses arquivos estejam no mesmo diretório ou no PYTHONPATH.
from game_of_life_sequential import GameOfLifeSequential
from game_of_life_parallel_threads import GameOfLifeParallelThreads
from game_of_life_distributed import GameOfLifeDistributed, DEFAULT_MASTER_PORT # Importa a classe distribuída e a porta padrão

def main():
    # --- Configurações da Simulação para Comparação ---
    # Para uma comparação significativa e para observar os benefícios do paralelismo/distribuição,
    # é fundamental usar grades maiores e um número substancial de gerações.
    # Grades muito pequenas (e.g., 10x10) ou poucas gerações (e.g., 5) podem fazer com que o overhead
    # de inicialização, sincronização e comunicação das versões otimizadas supere os ganhos,
    # resultando em tempos de execução mais lentos do que a versão sequencial.
    
    GRID_ROWS = 500     # Número de linhas da grade. Experimente com 1000, 2000 para cargas maiores.
    GRID_COLS = 500     # Número de colunas da grade.
    NUM_GENERATIONS = 50 # Número de gerações a simular. Um valor maior expõe melhor a eficiência do algoritmo.
    
    # Padrão inicial:
    # 'random': Gera um estado inicial aleatório, geralmente o melhor para benchmarking, pois
    #           cria um cenário de cálculo mais uniforme e imprevisível.
    # 'glider': Um padrão conhecido que se move pela grade. Útil para testes funcionais.
    # None: Inicia com uma grade vazia, onde nada acontece (útil para testar o overhead base).
    INITIAL_PATTERN = 'random' 
    
    # Número de threads para a versão paralela.
    # os.cpu_count(): Retorna o número de núcleos lógicos da CPU. É um bom ponto de partida.
    # Devido ao Global Interpreter Lock (GIL) do Python, para tarefas CPU-bound como o Game of Life,
    # o aumento do número de threads pode não escalar linearmente e, em alguns casos, pode até
    # degradar o desempenho devido ao overhead de gerenciamento de threads e contenção pelo GIL.
    # Experimente com 1, 2, 4, 8, etc., para analisar o impacto do GIL em sua máquina.
    NUM_THREADS = os.cpu_count() or 1 
    
    # Número de workers para a versão distribuída.
    # Para simular em uma única máquina, este valor pode ser igual ou menor que o número de núcleos da CPU.
    # Para um ambiente distribuído real (múltiplas máquinas), este seria o número total de processos worker
    # que você planeja iniciar em todas as máquinas.
    NUM_DISTRIBUTED_WORKERS = 4 
    
    # Visualização: SEMPRE DEVE SER FALSE para medições de desempenho precisas!
    # A visualização (impressão no console ou renderização gráfica) introduz um overhead de I/O significativo
    # que distorce os tempos de execução da lógica de simulação. Para benchmarking, o foco é o cálculo puro.
    VISUALIZE = False 

    # Lista para armazenar os objetos Popen dos processos worker, permitindo seu gerenciamento posterior.
    worker_processes = []

    print("======================================================================")
    print("           INICIANDO COMPARAÇÃO DAS VERSÕES DO JOGO DA VIDA           ")
    print("======================================================================")
    print(f"Configurações Globais da Simulação:")
    print(f"  Grade: {GRID_ROWS}x{GRID_COLS}")
    print(f"  Gerações: {NUM_GENERATIONS}")
    print(f"  Padrão Inicial: '{INITIAL_PATTERN}'")
    print(f"  Threads (Paralelo): {NUM_THREADS}")
    print(f"  Workers (Distribuído): {NUM_DISTRIBUTED_WORKERS}")
    print("======================================================================")

    # --- Execução da Versão SEQUENCIAL ---
    # Esta é a linha de base (baseline) para todas as comparações de desempenho.
    print("\n" + "#"*70)
    print("### Executando Versão SEQUENCIAL ###")
    print("#"*70)
    time_seq = None
    try:
        game_seq = GameOfLifeSequential(GRID_ROWS, GRID_COLS, initial_pattern=INITIAL_PATTERN)
        time_seq = game_seq.run_simulation(NUM_GENERATIONS, visualize=VISUALIZE)
        print(f"-> Tempo Sequencial: {time_seq:.4f} segundos.")
    except (ValueError, MemoryError, Exception) as e:
        print(f"ERRO na simulação sequencial: {type(e).__name__}: {e}")
        print("  Verifique se a grade é muito grande para a memória disponível ou se há um problema de inicialização.")
    print("#"*70 + "\n")

    # --- Execução da Versão PARALELA com THREADS ---
    # Avalia o desempenho do paralelismo baseado em threads, sujeito às limitações do GIL.
    print("\n" + "#"*70)
    print("### Executando Versão PARALELA com THREADS ###")
    print("#"*70)
    time_par = None
    try:
        game_par = GameOfLifeParallelThreads(GRID_ROWS, GRID_COLS, num_threads=NUM_THREADS, initial_pattern=INITIAL_PATTERN)
        time_par = game_par.run_simulation(NUM_GENERATIONS, visualize=VISUALIZE)
        print(f"-> Tempo Paralelo ({NUM_THREADS} threads): {time_par:.4f} segundos.")
    except (ValueError, MemoryError, Exception) as e:
        print(f"ERRO na simulação paralela com threads: {type(e).__name__}: {e}")
        print("  Pode ser um problema de recursos ou lógica de threads. O GIL pode limitar ganhos de desempenho.")
    print("#"*70 + "\n")

    # --- Execução da Versão DISTRIBUÍDA (Master-Worker) ---
    # Esta versão utiliza processos separados e comunicação via socket, permitindo paralelismo real
    # (bypassando o GIL), mas introduzindo overhead de comunicação e serialização.
    print("\n" + "#"*70)
    print("### Executando Versão DISTRIBUÍDA (Master-Worker) ###")
    print("#"*70)
    time_dist = None
    try:
        # 1. Iniciar Workers em processos separados
        print(f"Iniciando {NUM_DISTRIBUTED_WORKERS} processos worker...")
        current_dir = os.path.dirname(os.path.abspath(__file__)) # Obtém o diretório atual do script para localizar o worker.
        worker_script_path = os.path.join(current_dir, "game_of_life_worker.py")
        
        for i in range(NUM_DISTRIBUTED_WORKERS):
            # Usamos subprocess.Popen para iniciar cada worker como um processo separado.
            # `sys.executable`: Garante que o mesmo interpretador Python que executa o script master
            #                   seja usado para os workers, evitando problemas de ambiente.
            # `-u`: Garante que a saída do Python seja não-bufferizada, útil para depuração em tempo real.
            # `127.0.0.1`: Endereço IP do master (localhost para testes na mesma máquina).
            # `str(DEFAULT_MASTER_PORT)`: A porta na qual o master estará escutando.
            cmd = [sys.executable, "-u", worker_script_path, "127.0.0.1", str(DEFAULT_MASTER_PORT)]
            
            # `stdout=subprocess.PIPE` e `stderr=subprocess.PIPE`: Redirecionam a saída dos workers
            # para o master, evitando poluição do console principal. Para depuração, pode-se usar `None`
            # para que os workers imprimam diretamente no console.
            # `bufsize=1`: Garante que a saída seja lida linha por linha, útil com `-u`.
            worker_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1)
            worker_processes.append(worker_proc)
            print(f"  Worker {i+1} iniciado (PID: {worker_proc.pid}).")
            time.sleep(0.2) # Pequena pausa para garantir que os workers tenham tempo de inicializar e se conectar.

        # 2. Iniciar o Master Distribuído
        game_dist = GameOfLifeDistributed(GRID_ROWS, GRID_COLS, NUM_DISTRIBUTED_WORKERS, initial_pattern=INITIAL_PATTERN, master_port=DEFAULT_MASTER_PORT)
        time_dist = game_dist.run_simulation(NUM_GENERATIONS, visualize=VISUALIZE)
        print(f"-> Tempo Distribuído ({NUM_DISTRIBUTED_WORKERS} workers): {time_dist:.4f} segundos.")

    except (ValueError, MemoryError, Exception) as e:
        print(f"ERRO na simulação distribuída: {type(e).__name__}: {e}")
        print("  Verifique a conectividade de rede, a disponibilidade da porta ou a lógica de comunicação.")
    finally:
        # 3. Encerrar Workers
        print("\nFinalizando processos worker...")
        for i, worker_proc in enumerate(worker_processes):
            if worker_proc.poll() is None: # Verifica se o processo ainda está rodando (None significa que está ativo).
                try:
                    # Tenta um encerramento gracioso primeiro.
                    # `terminate()` envia um sinal SIGTERM (Unix) ou CTRL_C_EVENT (Windows).
                    # Permite que o processo worker execute rotinas de limpeza.
                    worker_proc.terminate()
                    worker_proc.wait(timeout=5) # Espera até 5 segundos para o worker terminar.
                    
                    if worker_proc.poll() is None: # Se o processo ainda não terminou após o timeout.
                        print(f"  Worker {i+1} (PID: {worker_proc.pid}) não terminou graciosamente. Forçando encerramento.")
                        # `kill()` envia um sinal SIGKILL (Unix) ou termina o processo imediatamente (Windows).
                        # Não permite que o processo execute rotinas de limpeza.
                        worker_proc.kill() 
                except Exception as ex:
                    print(f"  Erro ao tentar encerrar Worker {i+1} (PID: {worker_proc.pid}): {type(ex).__name__}: {ex}")
            
            # Opcional: Ler e imprimir a saída dos workers para depuração.
            # Útil para entender o que aconteceu se um worker falhou.
            stdout, stderr = worker_proc.communicate()
            if stdout: 
                print(f"  Worker {i+1} (PID: {worker_proc.pid}) STDOUT:\n{stdout.decode().strip()}")
            if stderr: 
                print(f"  Worker {i+1} (PID: {worker_proc.pid}) STDERR:\n{stderr.decode().strip()}")
            
            print(f"  Worker {i+1} (PID: {worker_proc.pid}) finalizado. Código de Retorno: {worker_proc.returncode}")
        print("#"*70 + "\n")


    # --- RELATÓRIO FINAL DE COMPARAÇÃO ---
    print("\n" + "="*70)
    print("               RELATÓRIO DE COMPARAÇÃO FINAL               ")
    print("======================================================================")
    print(f"Configuração da Simulação:")
    print(f"  Grade: {GRID_ROWS}x{GRID_COLS}")
    print(f"  Gerações: {NUM_GENERATIONS}")
    print(f"  Padrão Inicial: '{INITIAL_PATTERN}'")
    print(f"\nResultados de Tempo:")
    
    if time_seq is not None:
        print(f"  Tempo Sequencial: {time_seq:.4f} segundos")
    else:
        print(f"  Tempo Sequencial: N/A (Erro ou não executado)")

    if time_par is not None:
        print(f"  Tempo Paralelo ({NUM_THREADS} threads): {time_par:.4f} segundos")
    else:
        print(f"  Tempo Paralelo (Threads): N/A (Erro ou não executado)")

    if time_dist is not None:
        print(f"  Tempo Distribuído ({NUM_DISTRIBUTED_WORKERS} workers): {time_dist:.4f} segundos")
    else:
        print(f"  Tempo Distribuído (Workers): N/A (Erro ou não executado)")
    
    print("\nAnálise de Speedup (vs. Sequencial):")
    
    if time_seq is not None and time_seq > 0:
        if time_par is not None and time_par > 0:
            speedup_par = time_seq / time_par
            print(f"  Speedup Paralelo (Threads): {speedup_par:.2f}x")
            if speedup_par > 1.1: 
                print("    (Ganhos de desempenho observados, mas o GIL pode limitar a escalabilidade.)")
            elif speedup_par < 0.9: 
                print("    (Perda de desempenho, provavelmente devido ao overhead de threads e contenção pelo GIL.)")
            else: 
                print("    (Desempenho similar, indicando que o paralelismo de threads não trouxe benefícios significativos aqui.)")
        else:
            print("  Speedup Paralelo (Threads): N/A (Erro na execução paralela)")

        if time_dist is not None and time_dist > 0:
            speedup_dist = time_seq / time_dist
            print(f"  Speedup Distribuído (Workers): {speedup_dist:.2f}x")
            if speedup_dist > 1.1: 
                print("    (Ganhos de desempenho significativos, explorando o paralelismo real entre processos.)")
            elif speedup_dist < 0.9: 
                print("    (Perda de desempenho, provavelmente devido ao alto overhead de comunicação e serialização.)")
            else: 
                print("    (Desempenho similar, o overhead de comunicação pode estar anulando os ganhos de paralelismo.)")
        else:
            print("  Speedup Distribuído (Workers): N/A (Erro na execução distribuída)")
    else:
        print("  Não é possível calcular speedup sem o tempo da versão sequencial ou se ela falhou.")

    print("\n--- Considerações Finais ---")
    print("  - O módulo 'threading' em Python é limitado pelo Global Interpreter Lock (GIL) para tarefas CPU-bound.")
    print("    Isso significa que apenas uma thread Python pode executar bytecode Python por vez. ")
    print("    Portanto, a versão com threads pode não apresentar speedup significativo ou até ser mais lenta ")
    print("    devido ao overhead de gerenciamento de threads e trocas de contexto.")
    print("  - A versão distribuída (utilizando processos via `multiprocessing` ou comunicação via sockets) ")
    print("    pode oferecer paralelismo real, pois cada processo tem seu próprio interpretador Python e GIL.")
    print("    No entanto, ela introduz um overhead considerável de comunicação (network latency e bandwidth) ")
    print("    e serialização/desserialização de dados (e.g., usando `pickle`).")
    print("  - O Game of Life é um problema 'embarrassingly parallel' (paralelizável de forma trivial) em sua essência,")
    print("    pois o cálculo de cada célula é independente das outras, exceto por seus vizinhos diretos.")
    print("    Isso o torna um excelente candidato para paralelização, desde que o overhead de comunicação seja minimizado.")
    print("  - Otimizações para a versão distribuída podem incluir: ")
    print("    - **Redução da frequência de comunicação:** Em vez de trocar dados a cada geração, os workers poderiam ")
    print("      processar múltiplos passos (gerações) localmente antes de sincronizar o estado das `ghost cells` ou ")
    print("      retornar o resultado final ao master. Isso minimiza o número de interações de rede.")
    print("    - **Formato de serialização mais eficiente:** Substituir `pickle` por alternativas mais rápidas e compactas ")
    print("      para dados numéricos, como Protocol Buffers, MessagePack, ou a serialização binária nativa do NumPy (`ndarray.tobytes()`).")
    print("    - **Compressão de dados:** Comprimir os dados das `ghost cells` antes do envio pela rede para reduzir o volume de tráfego.")
    print("    - **Balanceamento de carga dinâmico:** Em vez de uma divisão estática da grade, um pool de tarefas onde workers pegam ")
    print("      novos chunks de trabalho quando terminam os anteriores pode melhorar a utilização de recursos, especialmente ")
    print("      se algumas regiões da grade forem mais 'ativas' (mais cálculos) do que outras.")
    print("    - **Utilização de frameworks:** Para sistemas distribuídos mais robustos, frameworks como `dask.distributed`, Ray, ")
    print("      ou Apache Spark (com `PySpark`) oferecem abstrações de alto nível e otimizações para gerenciamento de recursos, ")
    print("      tolerância a falhas e agendamento de tarefas.")
    print("======================================================================")

if __name__ == "__main__":
    main()
