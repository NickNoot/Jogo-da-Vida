import numpy as np
import time
import os

class GameOfLifeSequential:
    """
    Implementação sequencial do Jogo da Vida de Conway usando NumPy.
    A grade é toroidal, ou seja, as bordas se conectam.
    """
    
    # Constantes para representar os estados das células
    DEAD = 0
    ALIVE = 1

    def __init__(self, rows, cols, initial_pattern=None):
        """
        Inicializa a grade do Jogo da Vida.

        Args:
            rows (int): Número de linhas da grade. Deve ser um inteiro positivo.
            cols (int): Número de colunas da grade. Deve ser um inteiro positivo.
            initial_pattern (str, optional): Padrão inicial para a grade.
                                             Pode ser 'random' para um estado aleatório,
                                             'glider' para o padrão Glider, ou None para
                                             uma grade inicial vazia (todas as células mortas).
                                             Defaults to None.
        Raises:
            ValueError: Se as dimensões da grade forem inválidas ou o padrão inicial não for reconhecido.
        """
        if not (isinstance(rows, int) and rows > 0 and isinstance(cols, int) and cols > 0):
            raise ValueError("As dimensões da grade (rows, cols) devem ser inteiros positivos.")

        self.rows = rows
        self.cols = cols
        # A grade é inicializada com todas as células mortas (0).
        # Usamos dtype=int para garantir que os valores sejam 0 ou 1, otimizando o uso de memória.
        self.grid = np.zeros((self.rows, self.cols), dtype=int)

        # Aplica o padrão inicial conforme especificado
        if initial_pattern == 'random':
            self._initialize_random()
        elif initial_pattern == 'glider':
            self._initialize_glider()
        elif initial_pattern is None:
            pass # Grade já está vazia
        else:
            raise ValueError(f"Padrão inicial '{initial_pattern}' não reconhecido. Use 'random', 'glider' ou None.")

    def _initialize_random(self):
        """
        Inicializa a grade com células vivas (1) e mortas (0) aleatoriamente.
        Cada célula tem 50% de chance de estar viva.
        """
        self.grid = np.random.randint(self.DEAD, self.ALIVE + 1, size=(self.rows, self.cols), dtype=int)

    def _initialize_glider(self):
        """
        Inicializa a grade com um padrão Glider.
        O Glider é um dos padrões mais simples e conhecidos que se move pela grade.
        Requer uma grade de pelo menos 3x3 para ser visível.
        """
        # Verifica se a grade é grande o suficiente para o Glider
        if self.rows < 3 or self.cols < 3:
            print("Aviso: Grade muito pequena para um Glider (mínimo 3x3). Usando padrão aleatório.")
            self._initialize_random()
            return

        # Posição de início do glider (topo esquerdo, com um pequeno offset para evitar a borda imediata)
        # Este offset garante que o glider tenha espaço para se mover inicialmente.
        start_row, start_col = 1, 1 
        
        # O padrão Glider (5 células)
        # . # .
        # . . #
        # # # #
        
        # Certifica-se de que o glider não exceda os limites da grade
        if start_row + 2 >= self.rows or start_col + 2 >= self.cols:
            print("Aviso: Glider excede os limites da grade nesta posição. Usando padrão aleatório.")
            self._initialize_random()
            return

        # Linha 1 do glider
        self.grid[start_row, start_col + 1] = self.ALIVE
        # Linha 2 do glider
        self.grid[start_row + 1, start_col + 2] = self.ALIVE
        # Linha 3 do glider
        self.grid[start_row + 2, start_col] = self.ALIVE
        self.grid[start_row + 2, start_col + 1] = self.ALIVE
        self.grid[start_row + 2, start_col + 2] = self.ALIVE

    def _count_live_neighbors(self, r, c):
        """
        Conta o número de vizinhos vivos para uma célula específica (r, c).
        Usa condições de contorno toroidais (a grade se envolve, como no Pac-Man).

        Args:
            r (int): Índice da linha da célula.
            c (int): Índice da coluna da célula.

        Returns:
            int: O número de vizinhos vivos (0 a 8).
        """
        live_neighbors = 0
        # Itera sobre os 8 vizinhos (incluindo a própria célula no centro da iteração)
        for dr in [-1, 0, 1]:  # delta row
            for dc in [-1, 0, 1]:  # delta column
                if dr == 0 and dc == 0:  # Ignora a célula central (a própria célula)
                    continue

                # Calcula as coordenadas do vizinho com condições toroidais (wrap-around)
                # A operação `% self.rows` garante que o índice "volte" ao início da grade
                # se ultrapassar o limite superior ou inferior.
                neighbor_r = (r + dr + self.rows) % self.rows
                neighbor_c = (c + dc + self.cols) % self.cols

                # Adiciona o estado do vizinho (0 ou 1) à contagem
                live_neighbors += self.grid[neighbor_r, neighbor_c]
        return live_neighbors

    def _apply_rules(self, current_state, live_neighbors):
        """
        Aplica as quatro regras do Jogo da Vida de Conway para determinar o próximo
        estado de uma célula.

        Args:
            current_state (int): O estado atual da célula (0 para morta, 1 para viva).
            live_neighbors (int): O número de vizinhos vivos da célula.

        Returns:
            int: O próximo estado da célula (0 para morta, 1 para viva).
        """
        if current_state == self.ALIVE:  # Célula viva
            if live_neighbors < 2:  # Regra 1: Solidão (Underpopulation)
                return self.DEAD
            elif live_neighbors == 2 or live_neighbors == 3:  # Regra 2: Sobrevivência (Survival)
                return self.ALIVE
            else:  # live_neighbors > 3 (Regra 3: Superpopulação - Overpopulation)
                return self.DEAD
        else:  # current_state == self.DEAD (Célula morta)
            if live_neighbors == 3:  # Regra 4: Reprodução (Reproduction)
                return self.ALIVE
            else:
                return self.DEAD # Permanece morta

    def update(self):
        """
        Calcula a próxima geração da grade aplicando as regras do Jogo da Vida
        a cada célula. É crucial que todas as células sejam atualizadas com base
        no estado da geração *anterior* simultaneamente.
        """
        # Cria uma nova grade para armazenar os estados da próxima geração.
        # Isso evita que as atualizações de células afetem o cálculo de vizinhos
        # para outras células na mesma geração, garantindo a simultaneidade lógica.
        new_grid = np.zeros((self.rows, self.cols), dtype=int)

        # Percorre cada célula da grade atual
        for r in range(self.rows):
            for c in range(self.cols):
                # Conta os vizinhos vivos para a célula atual
                live_neighbors = self._count_live_neighbors(r, c)
                # Aplica as regras para determinar o estado futuro da célula
                new_grid[r, c] = self._apply_rules(self.grid[r, c], live_neighbors)
        
        # Atualiza a grade principal com a nova geração
        self.grid = new_grid

    def run_simulation(self, num_generations, visualize=False, clear_screen=True):
        """
        Executa a simulação por um número especificado de gerações.

        Args:
            num_generations (int): O número de gerações para simular.
            visualize (bool): Se True, imprime a grade a cada geração (para grades pequenas).
                              A visualização pode impactar significativamente o tempo de execução.
            clear_screen (bool): Se True, limpa o console antes de cada visualização para
                                 uma animação mais fluida. Ignorado se visualize for False.
        Returns:
            float: O tempo total de execução da simulação em segundos.
        """
        if visualize and (self.rows > 40 or self.cols > 80): # Limites ajustados para melhor experiência
            print("Aviso: A visualização pode ser muito lenta ou distorcida para grades grandes. Desativando visualização.")
            visualize = False

        print(f"Iniciando simulação sequencial para grade {self.rows}x{self.cols} com {num_generations} gerações...")
        start_time = time.perf_counter() # Usa perf_counter para medições de tempo mais precisas

        for gen in range(num_generations):
            if visualize:
                # Limpa o terminal para simular uma animação
                if clear_screen:
                    os.system('cls' if os.name == 'nt' else 'clear')
                print(f"Geração: {gen+1}/{num_generations}")
                self.print_grid()
                time.sleep(0.05) # Pequena pausa para tornar a visualização perceptível
            self.update() # Avança para a próxima geração

        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        print(f"\nSimulação sequencial concluída para {num_generations} gerações.")
        print(f"Tempo de execução: {elapsed_time:.4f} segundos")
        return elapsed_time

    def print_grid(self):
        """
        Imprime a grade atual no console.
        Células vivas são representadas por '#', células mortas por '.'.
        """
        # Para uma visualização mais compacta, podemos usar str.join
        for r in range(self.rows):
            # Substitui 0 por '.' e 1 por '#' para impressão
            row_str = "".join(["# " if cell == self.ALIVE else ". " for cell in self.grid[r]])
            print(row_str)
        print("-" * (self.cols * 2)) # Separador visual

# --- Exemplo de Uso ---
if __name__ == "__main__":
    # --- Configurações da Simulação ---
    GRID_ROWS = 50     # Número de linhas da grade (e.g., 20, 100, 500)
    GRID_COLS = 50    # Número de colunas da grade (e.g., 20, 100, 500)
    NUM_GENERATIONS = 100 # Número de gerações a simular (e.g., 50, 1000)
    
    # Padrão inicial:
    # 'random': Preenche a grade aleatoriamente. Bom para testes de desempenho.
    # 'glider': Adiciona um padrão Glider. Bom para verificar a correção das regras e movimento.
    # None: Inicia com uma grade vazia.
    INITIAL_PATTERN = 'random' 
    
    # Visualização:
    # True: Imprime a grade a cada geração. Útil para depuração e grades pequenas.
    # False: Não imprime a grade. Essencial para medições de desempenho precisas em grades maiores.
    VISUALIZE_SMALL_GRID = False 

    try:
        # Cria a instância da simulação
        game = GameOfLifeSequential(GRID_ROWS, GRID_COLS, initial_pattern=INITIAL_PATTERN)

        # Opcional: imprimir a grade inicial para verificar o setup
        # print("Grade Inicial:")
        # game.print_grid()

        # Executa a simulação e mede o tempo
        game.run_simulation(NUM_GENERATIONS, visualize=VISUALIZE_SMALL_GRID)

        # Opcional: imprimir a grade final
        # print("\nGrade Final:")
        # game.print_grid()

    except ValueError as e:
        print(f"Erro na configuração da simulação: {e}")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")
