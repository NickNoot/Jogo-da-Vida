import numpy as np
import time
import os
import threading # Embora ThreadPoolExecutor seja usado, threading é importado implicitamente
from concurrent.futures import ThreadPoolExecutor

# Importa a classe base da implementação sequencial
from game_of_life_sequential import GameOfLifeSequential

class GameOfLifeParallelThreads(GameOfLifeSequential):
    """
    Implementação paralela do Jogo da Vida de Conway usando threads através de ThreadPoolExecutor.
    Esta classe estende GameOfLifeSequential, reutilizando a lógica para contagem de vizinhos
    e aplicação de regras, mas paraleliza o cálculo da próxima geração.
    """
    def __init__(self, rows, cols, num_threads=None, initial_pattern=None):
        """
        Inicializa a grade e configura o número de threads.

        Args:
            rows (int): Número de linhas da grade.
            cols (int): Número de colunas da grade.
            num_threads (int, optional): Número de threads a serem usadas.
                                         Se None, usará o número de núcleos lógicos da CPU.
                                         Defaults to None.
            initial_pattern (str, optional): Padrão inicial da grade. Defaults to None.
        Raises:
            ValueError: Se num_threads for inválido.
        """
        # Chama o construtor da classe base (GameOfLifeSequential) para inicializar
        # a grade, suas dimensões e o padrão inicial.
        super().__init__(rows, cols, initial_pattern)
        
        # Define o número de threads a serem usadas.
        if num_threads is None:
            # os.cpu_count() retorna o número de CPUs no sistema (ou núcleos lógicos).
            # É um bom padrão para o número de threads em tarefas CPU-bound,
            # embora em Python o GIL possa limitar o paralelismo real.
            self.num_threads = os.cpu_count() or 1 
            print(f"Número de threads não especificado. Usando {self.num_threads} (núcleos lógicos da CPU).")
        else:
            if not isinstance(num_threads, int) or num_threads <= 0:
                raise ValueError("num_threads deve ser um inteiro positivo.")
            self.num_threads = num_threads

    def update(self):
        """
        Calcula a próxima geração da grade em paralelo usando threads.
        A grade é dividida horizontalmente (por linhas) entre as threads.
        Cada thread é responsável por calcular o estado de um subconjunto de linhas.
        """
        new_grid = np.zeros((self.rows, self.cols), dtype=int)
        
        def worker_task(start_row, end_row):
            """
            Função worker que será executada por cada thread.
            Ela processa um intervalo específico de linhas da grade.
            """
            for r in range(start_row, end_row):
                for c in range(self.cols):
                    # Reutiliza os métodos da classe base para a lógica central
                    live_neighbors = self._count_live_neighbors(r, c)
                    new_grid[r, c] = self._apply_rules(self.grid[r, c], live_neighbors)

        # ThreadPoolExecutor gerencia um pool de threads, distribuindo tarefas entre elas.
        # Ele é mais robusto e fácil de usar do que gerenciar threads manualmente.
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            futures = []
            # Divide as linhas da grade igualmente entre as threads.
            rows_per_thread = self.rows // self.num_threads
            
            for i in range(self.num_threads):
                start_row = i * rows_per_thread
                # A última thread lida com as linhas restantes para garantir que todas as linhas sejam processadas.
                end_row = (i + 1) * rows_per_thread if i < self.num_threads - 1 else self.rows
                
                # Submete a tarefa para o executor. submit() retorna um 'Future' object.
                futures.append(executor.submit(worker_task, start_row, end_row))
            
            # Chama .result() em cada Future para garantir que todas as tarefas foram concluídas
            # e para propagar quaisquer exceções que possam ter ocorrido nas threads.
            for future in futures:
                future.result() 
                
        self.grid = new_grid # Atualiza a grade principal com os resultados paralelos

    def run_simulation(self, num_generations, visualize=False, clear_screen=True):
        """
        Executa a simulação por um número especificado de gerações.
        Sobreescreve o método da classe base para incluir informações sobre
        o número de threads na mensagem de log.
        """
        if visualize and (self.rows > 40 or self.cols > 80):
            print("Aviso: A visualização pode ser muito lenta ou distorcida para grades grandes. Desativando visualização.")
            visualize = False

        print(f"Iniciando simulação PARALELA ({self.num_threads} threads) para grade {self.rows}x{self.cols} com {num_generations} gerações...")
        start_time = time.perf_counter()

        for gen in range(num_generations):
            if visualize:
                if clear_screen:
                    os.system('cls' if os.name == 'nt' else 'clear')
                print(f"Geração: {gen+1}/{num_generations}")
                self.print_grid()
                time.sleep(0.05)
            self.update()

        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        print(f"\nSimulação paralela concluída para {num_generations} gerações.")
        print(f"Tempo de execução: {elapsed_time:.4f} segundos")
        return elapsed_time

# --- Exemplo de Uso para Teste Rápido (Somente Paralelo) ---
# Este bloco só será executado se o script for chamado diretamente.
if __name__ == "__main__":
    print("--- Teste Rápido da Versão PARALELA com THREADS ---")
    # --- Configurações da Simulação ---
    GRID_ROWS = 500     # Número de linhas da grade
    GRID_COLS = 500     # Número de colunas da grade
    NUM_GENERATIONS = 100 # Número de gerações a simular
    INITIAL_PATTERN = 'random' # Padrão inicial: 'random', 'glider', ou None
    NUM_THREADS = None # Número de threads. Se None, usará os.cpu_count().
    VISUALIZE_SMALL_GRID = False # Apenas para grades pequenas para não impactar o desempenho

    try:
        game_par = GameOfLifeParallelThreads(GRID_ROWS, GRID_COLS, num_threads=NUM_THREADS, initial_pattern=INITIAL_PATTERN)
        time_par = game_par.run_simulation(NUM_GENERATIONS, visualize=VISUALIZE_SMALL_GRID)
    except ValueError as e:
        print(f"Erro na configuração da simulação paralela: {e}")
