from math import sin, cos
from micropython import const
from microqiskit import QuantumCircuit, simulate
from time import sleep
import pew

pew.init()

qc = QuantumCircuit(1,1)
qc.h(0)
qc.measure(0,0)

def randGen(): 
    digits = []
    for _ in range(3):
        counts = simulate(qc, shots=1, get='memory')
        digits += counts
    
    BinString = ''.join(digits)

    BinNum = int(BinString,2)

    return BinNum

__MAX_RAINDROPS = const(20)
__STARTING_SPEED = const(2)
__STARTING_Y = const(0)
__PLAYER_STARTING_X = const(3)
__PLAYER_STARTING_Y = const(7)
__DRAWING_COLOR = const(1)
__ERASING_COLOR = const(0)
__PLAYER_COLOR = const(255)
__GROUND_Y = const(7)
__SCREEN_MAX_X = const(7)
__SCREEN_MIN_X = const(0)
# Mods
__WRAP_AROUND = True
__DEFAULT_SPEED_FACTOR = 1.012
# Physics
__V_ZERO = __STARTING_SPEED
__PLANCK = 1

class AcidRain:
    def __init__(self):
        self.screen = pew.Pix()
        # Game stats
        self.player = (__PLAYER_STARTING_X, __PLAYER_STARTING_Y)
        self.old_player = (__PLAYER_STARTING_X, __PLAYER_STARTING_Y)
        self.reset_game_logic()
        self.game_speed = __STARTING_SPEED
        self.speed_factor = __DEFAULT_SPEED_FACTOR
        # Visuals
        self.title = pew.Pix.from_text("AcidRain")
        self.game_over = pew.Pix.from_text("Game Over!")

    # Utility functions
    def raindrops_are_too_close(self, A, B):
        return A[0] == B[0] and B[1] - A[1] == 1
    def raindrop_hit_the_ground(self, A):
        return A[1] == __GROUND_Y
    def raindrop_is_above_position(self, A, B):
        return A[0] == B[0] and A[1] == B[1] - 1
    def current_number_of_raindrops(self):
        return len(self.raindrops)
    def check_for_start(self):
        keys = pew.keys()
        return keys&pew.K_O or keys&pew.K_X
    def clear_screen_for_start(self):
        self.screen.box(0, x=0, y=0, width=8, height=8)
    def reset_game_logic(self):
        self.raindrops_evaded = 0
        self.to_draw = []
        self.to_erase = []
        self.raindrops = []
        self.game_speed = __STARTING_SPEED
    def new_raindrop(self):
        return randGen(), __STARTING_Y
    def debounce(self):
        for i in range(100):
            pew.tick(1/100)
            if not pew.keys():
                return

    # Game logic
    def generate_new_raindrops(self):
        how_many = 1
        current_number_of_raindrops = self.current_number_of_raindrops()
        if current_number_of_raindrops + how_many > __MAX_RAINDROPS:
            how_many = __MAX_RAINDROPS - current_number_of_raindrops
        new_raindrops = [self.new_raindrop() for i in range(how_many)]
        i = 0
        while i < how_many:
            while any(self.raindrops_are_too_close(new_raindrops[i], old) for old in self.raindrops):
                new_raindrops[i] = self.new_raindrop()
            i += 1
        # raindrops are safe to add now
        self.to_erase += self.raindrops
        self.to_draw += new_raindrops
        self.raindrops += new_raindrops
    def remove_fallen_raindrops(self):
        old_number_of_raindrops = self.current_number_of_raindrops()
        self.to_erase += list(filter(self.raindrop_hit_the_ground, self.raindrops))
        self.raindrops = list(filter(lambda x: not self.raindrop_hit_the_ground(x), self.raindrops))
        self.raindrops_evaded += old_number_of_raindrops - self.current_number_of_raindrops()
    def check_and_move_player(self):
        keys = pew.keys()
        self.debounce()
        x = self.player[0]
        dx = 0
        if keys & pew.K_UP:
            self.handle_quantum_tunnelling()
        else:
            if keys & pew.K_LEFT:
                dx -= 1
            elif keys & pew.K_RIGHT:
                dx += 1
            if x + dx > __SCREEN_MAX_X:
                dx = -7 if __WRAP_AROUND else 0
            if x + dx < __SCREEN_MIN_X:
                dx = 7 if __WRAP_AROUND else 0
            self.old_player = self.player[0], self.player[1]
            if dx: # actual movement
                self.player = x+dx, self.player[1]
    def handle_quantum_tunnelling(self):
        if any(self.raindrop_is_above_position(raindrop, self.player) for raindrop in self.raindrops):
            raindrop_above = self.player[0], self.player[1]-1

            a = 1
            m = 1

            # E = self.game_speed**2/2
            # k_0 = sqrt(2*m*E/__PLANCK**2)
            # k_1 = sqrt(2*m*(E-__V_ZERO)/__PLANCK**2)

            # t = 4*k_0*k_1*comp_exp(-1*a*(k_0-k_1))
            # t /= (k_0+k_1)**2 - comp_exp(2*a*k_1)*(k_0 - k_1)**2

            # t = 1 / ((k_0 - k_1)**4*sin(2*a*k_1)**2 + ((k_1+k_0)**2 - (k_0-k_1)**2*cos(2*a*k_1))**2 )
            # t = 1 - exp(-self.game_speed / 2)
            t = self.game_speed - self.game_speed**2/2 + self.game_speed**3/6

            if randGen()/7 <= t:
                if any(self.raindrop_is_above_position(raindrop, raindrop_above) for raindrop in self.raindrops):
                    raise pew.GameOver # die
                else:
                    self.to_erase.append(raindrop_above)
                    self.raindrops = list(filter(lambda x: x != raindrop_above, self.raindrops))
            else: # die
                raise pew.GameOver
    def check_for_player_collision(self):
        if any(self.player == raindrop for raindrop in self.raindrops):
            raise pew.GameOver
    def update_raindrops(self):
        for i in range(len(self.raindrops)):
            self.to_erase.append(self.raindrops[i])
            self.raindrops[i] = (self.raindrops[i][0], self.raindrops[i][1] + 1)
            self.to_draw.append(self.raindrops[i])

    def run_game(self):
        game_started = False
        # Title
        while True:
            for dx in range(-8, self.title.width):
                self.screen.blit(self.title, -dx, 1)
                pew.show(self.screen)
                pew.tick(1/12)
                game_started = self.check_for_start()
                if game_started: break
            if game_started: break
        # Game started
        self.clear_screen_for_start()
        try:
            while True:
                # Poll keys
                self.screen.pixel(*self.player, color=__ERASING_COLOR)
                self.check_and_move_player()
                self.screen.pixel(*self.player, color=__PLAYER_COLOR)
                #####################################
                self.remove_fallen_raindrops()
                self.update_raindrops()
                self.generate_new_raindrops()
                self.check_for_player_collision()
                # Update screen elements here
                while len(self.to_erase):
                    self.screen.pixel(*self.to_erase.pop(0), color=__ERASING_COLOR)
                while len(self.to_draw):
                    self.screen.pixel(*self.to_draw.pop(0), color=__DRAWING_COLOR)
                pew.show(self.screen)
                pew.tick(1/self.game_speed)
                self.game_speed *= self.speed_factor
        except pew.GameOver:
            # Game over screen
            self.clear_screen_for_start()
            for dx in range(-8, self.game_over.width):
                self.screen.blit(self.game_over, -dx, 1)
                pew.show(self.screen)
                pew.tick(1/17)
            score = pew.Pix.from_text("Score: " + str(self.raindrops_evaded))
            for dx in range(-8, score.width):
                self.screen.blit(score, -dx, 1)
                pew.show(self.screen)
                pew.tick(1/13)
            self.reset_game_logic()
            self.debounce() # for any other button presses
