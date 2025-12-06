import time
import os
import sys
import subprocess
import signal
import json # Para formatar a tabela de resultados

# Importa as classes das suas respectivas implementações
from game_of_life_sequential import GameOfLifeSequential
from game_of_life_parallel_threads import GameOfLifeParallelThreads
from game_of_life_distributed import GameOfLifeDistributed, DEFAULT_MASTER_PORT

def main():
    # --- Configurações da Simulação para Comparação ---
    # Lista de tamanhos de grade para testar. Cada tupla representa (linhas, colunas).
    # É crucial escolher uma gama de tamanhos que cubra desde pequenas grades (onde o overhead
    # do paralelismo pode ser maior que o ganho) até grandes grades (onde o paralelismo deve
    # teoricamente brilhar), e tamanhos intermediários para observar a transição.
    # Cuidado com MemoryError para grades muito grandes, dependendo da memória RAM disponível.
    GRID_SIZES = [(100, 100), (500, 500), (1000, 1000)]
    # Para testes rápidos durante o desenvolvimento, use um tamanho menor:
    # GRID_SIZES = [(200, 200)]
    
    NUM_GENERATIONS = 50 
    # Um número razoável de gerações é importante para que o tempo de execução
    # não seja dominado apenas pelo setup inicial, mas sim pela computação iterativa.
    INITIAL_PATTERN = 'random' 
    NUM_THREADS = os.cpu_count() or 1 
    # Usar o número de CPUs disponíveis é uma boa prática para threads,
    # embora o GIL em Python possa limitar o benefício real.
    NUM_DISTRIBUTED_WORKERS = 4 
    # O número de workers distribuídos pode ser ajustado. Para um ambiente local,
    # um número pequeno é suficiente para demonstrar a arquitetura.
    VISUALIZE = False 
    # SEMPRE FALSE para benchmarking preciso! A visualização adiciona um overhead
    # significativo que distorceria as medições de tempo de computação.

    # Lista para armazenar os resultados de cada execução para cada tamanho de grade
    all_results = []

    print("======================================================================")
    print("           INICIANDO COMPARAÇÃO DAS VERSÕES DO JOGO DA VIDA           ")
    print("======================================================================")
    print(f"Configurações Globais da Simulação:")
    print(f"  Gerações por teste: {NUM_GENERATIONS}")
    print(f"  Padrão Inicial: '{INITIAL_PATTERN}'")
    print(f"  Threads (Paralelo): {NUM_THREADS}")
    print(f"  Workers (Distribuído): {NUM_DISTRIBUTED_WORKERS}")
    print("======================================================================")

    # Loop principal para iterar sobre os diferentes tamanhos de grade
    for GRID_ROWS, GRID_COLS in GRID_SIZES:
        print(f"\n{'='*70}")
        print(f"--- EXECUTANDO PARA GRADE: {GRID_ROWS}x{GRID_COLS} ---")
        print(f"{'='*70}")

        current_grid_results = {
            "Grid Size": f"{GRID_ROWS}x{GRID_COLS}",
            "Sequential Time (s)": "N/A",
            "Parallel Time (s)": "N/A",
            "Parallel Speedup": "N/A",
            "Distributed Time (s)": "N/A",
            "Distributed Speedup": "N/A"
        }
        
        # Lista para armazenar os objetos Popen dos processos worker
        worker_processes = []
        
        # --- Execução da Versão SEQUENCIAL ---
        print("\n" + "#"*70)
        print(f"### Executando Versão SEQUENCIAL ({GRID_ROWS}x{GRID_COLS}) ###")
        print("#"*70)
        time_seq = None
        try:
            game_seq = GameOfLifeSequential(GRID_ROWS, GRID_COLS, initial_pattern=INITIAL_PATTERN)
            time_seq = game_seq.run_simulation(NUM_GENERATIONS, visualize=VISUALIZE)
            print(f"-> Tempo Sequencial: {time_seq:.4f} segundos.")
            current_grid_results["Sequential Time (s)"] = round(time_seq, 4)
        except MemoryError as e:
            print(f"ERRO de memória na simulação sequencial para {GRID_ROWS}x{GRID_COLS}: {e}")
            print("  Skipping sequential for this grid size due to MemoryError.")
        except Exception as e:
            print(f"ERRO inesperado na simulação sequencial: {type(e).__name__}: {e}")
            print("  Skipping sequential for this grid size.")
        print("#"*70 + "\n")

        # --- Execução da Versão PARALELA com THREADS ---
        print("\n" + "#"*70)
        print(f"### Executando Versão PARALELA com THREADS ({GRID_ROWS}x{GRID_COLS}) ###")
        print("#"*70)
        time_par = None
        try:
            game_par = GameOfLifeParallelThreads(GRID_ROWS, GRID_COLS, num_threads=NUM_THREADS, initial_pattern=INITIAL_PATTERN)
            time_par = game_par.run_simulation(NUM_GENERATIONS, visualize=VISUALIZE)
            print(f"-> Tempo Paralelo ({NUM_THREADS} threads): {time_par:.4f} segundos.")
            current_grid_results["Parallel Time (s)"] = round(time_par, 4)
            if time_seq is not None and time_par > 0:
                speedup_par = time_seq / time_par
                current_grid_results["Parallel Speedup"] = round(speedup_par, 2)
        except MemoryError as e:
            print(f"ERRO de memória na simulação paralela para {GRID_ROWS}x{GRID_COLS}: {e}")
            print("  Skipping parallel for this grid size due to MemoryError.")
        except Exception as e:
            print(f"ERRO inesperado na simulação paralela com threads: {type(e).__name__}: {e}")
            print("  Skipping parallel for this grid size.")
        print("#"*70 + "\n")

        # --- Execução da Versão DISTRIBUÍDA (Master-Worker) ---
        print("\n" + "#"*70)
        print(f"### Executando Versão DISTRIBUÍDA (Master-Worker) ({GRID_ROWS}x{GRID_COLS}) ###")
        print("#"*70)
        time_dist = None
        try:
            # 1. Iniciar Workers em processos separados
            print(f"Iniciando {NUM_DISTRIBUTED_WORKERS} processos worker para {GRID_ROWS}x{GRID_COLS}...")
            current_dir = os.path.dirname(os.path.abspath(__file__)) 
            worker_script_path = os.path.join(current_dir, "game_of_life_worker.py")
            
            for i in range(NUM_DISTRIBUTED_WORKERS):
                cmd = [sys.executable, "-u", worker_script_path, "127.0.0.1", str(DEFAULT_MASTER_PORT)]
                # Redirecionar stdout/stderr para arquivos de log separados para evitar poluir o console principal
                # e facilitar a depuração de workers individuais.
                # O parâmetro 'bufsize=1' força o flush imediato do buffer de saída, útil para logs em tempo real.
                worker_log_file = open(f"worker_{i+1}_grid_{GRID_ROWS}x{GRID_COLS}.log", "w")
                worker_proc = subprocess.Popen(cmd, stdout=worker_log_file, stderr=subprocess.STDOUT, bufsize=1)
                worker_processes.append((worker_proc, worker_log_file)) # Armazena o proc e o arquivo de log
                print(f"  Worker {i+1} iniciado (PID: {worker_proc.pid}), log em worker_{i+1}_grid_{GRID_ROWS}x{GRID_COLS}.log")
                # Pequena pausa para garantir que os workers tenham tempo de inicializar e se conectar ao master.
                # Em sistemas distribuídos reais, um mecanismo de handshake explícito seria mais robusto.
                time.sleep(0.5) 
            
            # 2. Iniciar o Master Distribuído
            game_dist = GameOfLifeDistributed(GRID_ROWS, GRID_COLS, NUM_DISTRIBUTED_WORKERS, initial_pattern=INITIAL_PATTERN, master_port=DEFAULT_MASTER_PORT)
            time_dist = game_dist.run_simulation(NUM_GENERATIONS, visualize=VISUALIZE)
            print(f"-> Tempo Distribuído ({NUM_DISTRIBUTED_WORKERS} workers): {time_dist:.4f} segundos.")
            current_grid_results["Distributed Time (s)"] = round(time_dist, 4)
            if time_seq is not None and time_dist > 0:
                speedup_dist = time_seq / time_dist
                current_grid_results["Distributed Speedup"] = round(speedup_dist, 2)

        except MemoryError as e:
            print(f"ERRO de memória na simulação distribuída para {GRID_ROWS}x{GRID_COLS}: {e}")
            print("  Skipping distributed for this grid size due to MemoryError.")
        except Exception as e:
            print(f"ERRO inesperado na simulação distribuída: {type(e).__name__}: {e}")
            print("  Skipping distributed for this grid size.")
        finally:
            # 3. Encerrar Workers lançados para este tamanho de grade de forma graciosa
            print("\nFinalizando processos worker para esta rodada...")
            for i, (worker_proc, log_file) in enumerate(worker_processes):
                if worker_proc.poll() is None: # Verifica se o processo ainda está rodando
                    try:
                        # Tenta encerrar o processo graciosamente (SIGTERM)
                        worker_proc.terminate()
                        # Espera um tempo limitado para o processo terminar.
                        worker_proc.wait(timeout=5) 
                        if worker_proc.poll() is None: # Se ainda estiver rodando após o timeout
                            print(f"  Worker {i+1} (PID: {worker_proc.pid}) não terminou graciosamente. Forçando encerramento (SIGKILL).")
                            worker_proc.kill() # Encerramento forçado
                    except Exception as ex:
                        print(f"  Erro ao tentar encerrar Worker {i+1} (PID: {worker_proc.pid}): {type(ex).__name__}: {ex}")
                
                # Garante que o arquivo de log do worker seja fechado, liberando o recurso.
                log_file.close() 
                print(f"  Worker {i+1} (PID: {worker_proc.pid}) finalizado. Código de Retorno: {worker_proc.returncode}")
            print("#"*70 + "\n")

        all_results.append(current_grid_results) # Adiciona os resultados desta grade à lista geral

    # --- RELATÓRIO FINAL DE COMPARAÇÃO ---
    print("\n" + "="*70)
    print("               RELATÓRIO DE COMPARAÇÃO FINAL               ")
    print("======================================================================")
    print("\nSumário dos Resultados por Tamanho de Grade:")
    
    # Gerar a tabela no formato especificado
    if all_results:
        # Extrai os cabeçalhos das chaves do primeiro dicionário de resultados para garantir consistência
        headers = list(all_results[0].keys())
        
        # Inicia a estrutura da tabela HTML para facilitar a integração em documentação ou relatórios.
        html_table = '<table class="data-table">\n'
        html_table += '  <thead>\n'
        html_table += '    <tr>\n'
        for header in headers:
            html_table += f'      <th scope="col">{header}</th>\n'
        html_table += '    </tr>\n'
        html_table += '  </thead>\n'
        html_table += '  <tbody>\n'
        
        for result in all_results:
            html_table += '    <tr>\n'
            for header in headers:
                value = result.get(header, "N/A") # Usa get() com default para robustez
                html_table += f'      <td>{value}</td>\n'
            html_table += '    </tr>\n'
        html_table += '  </tbody>\n'
        html_table += '</table>'
        
        print(html_table) # Imprime a tabela formatada

    print("\n--- Análise de Escalabilidade e Considerações Finais ---")
    print("  Ao analisar a tabela acima, observe como os 'Speedup' variam com o aumento do 'Grid Size'.")
    print("  Um 'Speedup' maior que 1 indica que a versão paralela/distribuída é mais rápida que a sequencial.")
    print("  Um 'Speedup' menor que 1 (ou tempo maior) indica que o overhead do paralelismo superou os ganhos.")
    print("  - **Versão Sequencial:** Serve como a linha de base (baseline) para todas as comparações de desempenho.")
    print("    Seu tempo de execução deve crescer de forma previsível com o aumento do tamanho da grade (tipicamente O(N*M*G) onde N, M são dimensões e G gerações).")
    print("  - **Versão Paralela (Threads):** Para problemas CPU-bound em Python, o Global Interpreter Lock (GIL)")
    print("    tende a limitar o speedup em processadores multi-core. Embora múltiplas threads possam estar ativas,")
    print("    apenas uma pode executar bytecode Python por vez. Em grades maiores, o overhead de gerenciamento e sincronização de threads")
    print("    (trocas de contexto, locks) pode se tornar mais pronunciado, e o ganho real de desempenho pode não ser linear ou até diminuir (speedup < 1) devido ao overhead.")
    print("    O speedup observado raramente excederá o número de núcleos físicos para tarefas intensivas em CPU.")
    print("  - **Versão Distribuída (Workers):** Esta versão contorna o GIL usando processos separados, que podem ser executados")
    print("    em núcleos de CPU distintos simultaneamente. No entanto, introduz um custo significativo de comunicação (serialização/desserialização de dados e latência de rede)")
    print("    para a troca de 'ghost cells' (células de fronteira) entre o master e os workers em cada geração. Para grades")
    print("    menores, o overhead de comunicação pode anular completamente os benefícios do paralelismo, resultando")
    print("    em um desempenho pior que o sequencial (speedup < 1). No entanto, para grades muito grandes, onde o tempo de cálculo")
    print("    local de cada worker é substancialmente maior que o tempo de comunicação das 'ghost cells', os ganhos")
    print("    do paralelismo real tendem a se manifestar mais claramente, e o speedup pode se aproximar do número de workers (idealmente).")
    print("    A eficiência desta abordagem depende criticamente da relação entre o tempo de computação e o tempo de comunicação.")
    print("  - **Escalabilidade Ideal:** Uma solução ideal mostraria um 'Speedup' crescente à medida que o 'Grid Size' aumenta,")
    print("    indicando que a abordagem paralela/distribuída está se tornando mais eficiente à medida que a carga de trabalho cresce.")
    print("    Se o speedup diminuir ou se estabilizar em um valor baixo, isso indica um gargalo (GIL, comunicação excessiva, sincronização ineficiente ou balanceamento de carga pobre).")
    print("    A Lei de Amdahl e a Lei de Gustafson são conceitos relevantes para entender os limites teóricos do speedup.")
    print("======================================================================")

if __name__ == "__main__":
    main()
