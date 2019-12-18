from micropython import const
from microqiskit import QuantumCircuit, simulate
import pew

# Game settings
__RAINDROP_STARTING_Y = const(0)
__STARTING_SPEED = const(2)
__PLAYER_STARTING_X = const(3)
__RAIN_COLOUR = const(1)
__PLAYER_COLOUR = const(255)
__ERASING_COLOUR = const(0)
__GROUND_Y = const(7)
__SCREEN_MIN_X = const(0)
__SCREEN_MAX_X = const(7)
__GAME_SPEED_FACTOR = 1.012
__TITLE_SCREEN = pew.Pix.from_text('AcidRain')
__GAME_OVER_SCREEN = pew.Pix.from_text('Game Over!')
__V_0 = const(20)
# In the case where the player reaches game_speed >= __V_0,
# we distinguish them by displaying __EASTER_EGG:
__EASTER_EGG = pew.Pix.from_text("Congratulations! You've won! ^-^")
class __YouAreSpecial(Exception):
	pass

# Game mods
__WRAP_AROUND = True
__SIMULATING_REAL_PHYSICS = True

# Physics
if __SIMULATING_REAL_PHYSICS:
	from math import sqrt, exp
	def cosh(x): return (exp(x) + exp(-x))/2
	"""
		Representing the mass of the player by __MASS, and noticing that when
		E >= __V_0 we end the game, we calculate the wave number K1 by:
		
		_K1	= sqrt((2*__MASS*(__V_0 - E)) / h_bar)
				= sqrt(2*__MASS/h_bar) * sqrt(__V_0 - E)
				of which we can store the constant part.
		
		Since h_bar is pretty small, sqrt(1/h_bar) will be large, so to bring
		the number into a relatively normal range, we'll choose __MASS and __A,
		the width of the raindrop, to be relatively smaller.
	"""
	__MASS = 1e-18
	__A = 1e-9
	__OFFSET = 0.0001
	__K_1 = sqrt(2*__MASS/1.054571817e-34) # 1.054571817e-34 is the reduced Planck constant
	"""
		The probability of transmission through the raindrop when E < __V_0 is
		given by:

		t = 1 / (1 + (__V_0**2*sinh(_K1*__A)**2) / (4*E*(__V_0 - E)))
		
		For reasons that I didn't notice were unnecessary until the point of writing,
		we make use of:

		sinh(x)**2 = (cosh(2x) - 1)/2

		we change this to:

		t = 1 / (1 + (__V_0**2*(cosh(2*_K1*__A) - 1)) / (8*E*(__V_0 - E)) )

		We'll accept the probability as being convincing if it is larger than 0.5.
	"""

# MicroQiskit
qc = QuantumCircuit(1,1)
qc.h(0)
qc.measure(0,0)
def rand():
	return int(''.join(simulate(qc, shots=3, get='memory')), 2)

# Game variables
sc = pew.Pix()
player = __PLAYER_STARTING_X
raindrops_evaded = 0
raindrops = []
game_speed = __STARTING_SPEED

# Game logic/utility functions
def reset_game_logic():
	global player, raindrops_evaded, raindrops, game_speed
	player = __PLAYER_STARTING_X
	raindrops_evaded = 0
	raindrops = []
	game_speed = __STARTING_SPEED

def debounce():
	if game_speed < 2.2:
		t = 75
	elif game_speed < 2.5:
		t = 50
	else:
		t = 40
	for _ in range(100):
		pew.tick(1/t)
		if not pew.keys():
			return

def check_and_move_player():
	k = pew.keys()
	debounce()
	if k & pew.K_UP:
		handle_quantum_tunnelling()
	else:
		if k & pew.K_LEFT:
			dx = -1
		elif k & pew.K_RIGHT:
			dx = 1
		else:
			return
		global player
		if player + dx > __SCREEN_MAX_X:
			dx = -7 if __WRAP_AROUND else 0
		if player + dx < __SCREEN_MIN_X:
			dx = 7 if __WRAP_AROUND else 0
		sc.pixel(player, __GROUND_Y, color=__ERASING_COLOUR)
		player += dx
		sc.pixel(player, __GROUND_Y, color=__PLAYER_COLOUR)

def handle_quantum_tunnelling():
	global raindrops_evaded
	if any(r[0] == player and r[1] == __GROUND_Y-1 for r in raindrops):
		# check if there is a raindrop directly above the raindrop directly
		# above the player, because quantum tunnelling is only for one raindrop
		if any(r[0] == player and r[1] == __GROUND_Y-2 for r in raindrops):
			raise pew.GameOver

		if __SIMULATING_REAL_PHYSICS:
			E = game_speed - __STARTING_SPEED + __OFFSET
			k_1 = __K_1 * sqrt(__V_0 - E)
			t = __V_0**2 * (cosh(2 * k_1 * __A) - 1)
			t /= 8 * E * (__V_0 - E)
			t += 1
			if 1/t < 0.5: # survives
				sc.pixel(player, __GROUND_Y-1, color=__ERASING_COLOUR)
				raindrops.remove([player, __GROUND_Y-1])
				raindrops_evaded += 1
			else: # die
				raise pew.GameOver
		else:
			if int(*simulate(qc, shots=1, get='memory')) < 1: # survives
				sc.pixel(player, __GROUND_Y-1, color=__ERASING_COLOUR)
				raindrops.remove([player, __GROUND_Y-1])
				raindrops_evaded += 1
			else: # die
				raise pew.GameOver

# Actual game
pew.init() # otherwise sc is None
while True:

	game_started = False
	while True:
		for dx in range(-8, __TITLE_SCREEN.width):
			sc.blit(__TITLE_SCREEN, -dx, 1)
			pew.show(sc)
			pew.tick(1/12)
			game_started = pew.keys() & (pew.K_O | pew.K_X)
			if game_started: break
		if game_started: break
	sc.box(0, x=0, y=0, width=8, height=8)
	sc.pixel(player, __GROUND_Y, color=__PLAYER_COLOUR) # draw the player for the first time
	try:
		while True:
			check_and_move_player()
			for i in range(len(raindrops)-1, -1, -1):
				# remove fallen raindrops
				if raindrops[i][1] == __GROUND_Y:
					sc.pixel(*raindrops[i], color=__ERASING_COLOUR)
					del raindrops[i]
					raindrops_evaded += 1
					# fairly certain redrawing the player here fixed a visual bug
					sc.pixel(player, __GROUND_Y, color=__PLAYER_COLOUR)
				# update raindrops
				else:
					sc.pixel(*raindrops[i], color=__ERASING_COLOUR)
					raindrops[i][1] += 1
					sc.pixel(*raindrops[i], color=__RAIN_COLOUR)
				# check for player collision
				if raindrops[i] == [player, __GROUND_Y]:
					raise pew.GameOver
				# generate new raindrop
			raindrops.append([rand(), __RAINDROP_STARTING_Y-1])
			if game_speed >= __V_0:
				raise __YouAreSpecial
			pew.show(sc)
			pew.tick(1/game_speed)
			game_speed *= __GAME_SPEED_FACTOR
	except (pew.GameOver, __YouAreSpecial) as e:
		sc.box(0, x=0, y=0, width=8, height=8)
		score = pew.Pix.from_text('Score: ' + str(raindrops_evaded))
		p = __GAME_OVER_SCREEN if isinstance(e, pew.GameOver) else __EASTER_EGG
		for dx in range(-8, p.width):
			sc.blit(p, -dx, 1)
			pew.show(sc)
			pew.tick(1/17)
		for dx in range(-8, score.width):
			sc.blit(score, -dx, 1)
			pew.show(sc)
			pew.tick(1/13)
		# Reset game logic
		reset_game_logic()
		debounce() # useful
