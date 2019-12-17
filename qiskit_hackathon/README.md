# AcidRain

_Avoid the rain because it's acid._ A simple directive meant for a simple game, add to that a quantum twist and you've got **AcidRain**.

## Qiskit hackathon

The availability of a **[PewPew v10.2](https://pewpew.readthedocs.io/en/latest/pewpew10/overview.html)** sparked the idea for a handheld game written in [MicroPython](https://micropython.org) (a Python implementation for microcontrollers) but with a quantum twist, as per the hackathon's theme.

The PewPew v10.2 is the fruit of [@deshipu](https://github.com/deshipu)'s labour. [Documentation is available here](https://pewpew.readthedocs.io/en/latest/pew.html) and [source code here](https://github.com/pewpew-game/pewpew/blob/master/libs/PewPew10.2/frozen/pewpew10/pew.py).

Thanks to the efforts of [@quantumjim](https://github.com/quantumjim) there exists [MicroQiskit](https://github.com/quantumjim/MicroQiskit), a "version of Qiskit that could run on microcontrollers" and more specifically a MicroPython-compatible version.

We now have the essential building blocks for a handheld quantum game, now we only need make it.

### Game development

#### Beginnings

With the PewPew's 8x8 LED matrix, the game had the challenge of being entertaining with a small visual footprint. This naturally led to the use of single pixels to represent game elements.

Opting for an object-oriented + endless while loop approach, we first decide to implement a modular non-quantum version of the game. This lets us debug core game elements and logic while leaving room for future plug-ins.

```python
import pew

pew.init()

class AcidRain:
    def __init__(self):
        self.screen = pew.Pix()

    def run_game(self):
        pass
```

We call the `pew.init` function at the start of our code. If other modules were to import our code then the PewPew's initialisation would happen in the background, a feature that seems desirable.

Next we add variables for game logic.

We'll keep a list of all raindrop positions to display on screen, as well as the player's position, position being represented by a 2-tuple. The PewPew, when held with onboard text in the right direction, has its top left pixel at position `(0,0)` and the bottom right at `(7,7)`: we'll place the player on the 'ground' and preferably close to the middle.

We'll keep track of 'fallen' raindrops to represent score, as well as store the title and game-over screens.

```python
# [...]
class AcidRain:
    def __init__(self):
        self.screen = pew.Pix()
        # Game stats
        self.player = 3,7
        self.raindrops = []
        self.raindrops_evaded = 0
        # Visuals
        self.title = pew.Pix.from_text('AcidRain')
        self.game_over = pew.Pix.from_text('Game Over!')
    # [...]
```

#### Making it rain

##### Capping success

We'd like to limit the amount of raindrops to keep the game playable at faster speeds, so we'll add:

```python
from micropython import const
import pew

__MAX_RAINDROPS = const(20)

# [...]
```

`const` is similar to the `#define` pre-processor directive in C, which carries out literal replacement of a value wherever the variable is mentioned, saving memory. The double underscores at the beginning of a variable name prevent the variable from being loaded into the global dictionary: we choose to do so because we don't need/want the variable to be accessible at runtime.

Both of these are functionally-speaking unnecessary, but good practise when dealing with microcontrollers as they don't have the same memory abundance as everyday computers.

##### Generating success

```python
from micropython import const
from random import random
import pew

# [...]

__STARTING_Y = const(0)

class AcidRain:
    # [...]
    def generate_new_raindrops(self):
        how_many = 1
        current_number_of_raindrops = self.current_number_of_raindrops()
        # check cap
        if current_number_of_raindrops + how_many > __MAX_RAINDROPS:
            how_many = __MAX_RAINDROPS - current_number_of_raindrops
        new_raindrops = [self.new_raindrop() for i in range(how_many)]
        self.raindrops += new_raindrops

    def current_number_of_raindrops(self):
        return len(self.raindrops)
    def new_raindrop(self):
        return round(random()*7), __STARTING_Y

    # [...]
```

We initially envisioned generating multiple raindrops between every screen update, however after some thinking (and later playtesting) generating a single raindrop proved to be enough of a challenge.

`new_raindrop` makes use of the `random` library to generate a random number between 0 and 7 for the x-component. The y-component is set to 0, which corresponds to the 'sky'.

An improvement we can make to raindrop generation is checking that none of the generated raindrops are 'too close' to any pre-existing raindrops so that the game remains playable.

```python
# [...]
class AcidRain:
    # [...]
    def generate_new_raindrops(self):
        # [...]
        new_raindrops = [self.new_raindrop() for i in range(how_many)]
        i = 0
        while i < how_many:
            while any(self.raindrops_are_too_close(new_raindrops[i], old) for old in self.raindrops):
                new_raindrops[i] = self.new_raindrop()
            i += 1
        # raindrops are safe to add now
        self.raindrops += new_raindrops
    # [...]
    def raindrops_are_too_close(self, A, B):
        return A[0] == B[0] and B[1] - A[1] == 1
    # [...]
```

`self.raindrops_are_too_close(new_raindrops[i], old)` checks if the newly generated raindrop is right above any pre-existing raindrop. We'd want to prevent this because we could accidentally stack raindrops, which could create certain unavoidable deaths when playing the game.

##### Moving success

The raindrops should fall downwards during the game. We obtain this effect by decrementing each raindrops' y-component by 1.

```python
# [...]
class AcidRain:
    # [...]
    def update_raindrops(self):
        for i in range(len(self.raindrops)):
            self.raindrops[i] = (self.raindrops[i][0], self.raindrops[i][1] + 1)
    # [...]
```

Python does not allow tuple overwriting which is why we're redefining each raindrop as a new tuple from its original coordinates.

##### Eliminating success

Once a raindrop hits the ground, we'd like to remove it from the maintained list of raindrops. For our score we'd also like to add the amount of fallen raindrops to the total amount of raindrops evaded, so it would make sense to handle that here as well.

```python
# [...]
class AcidRain:
    # [...]
    def remove_fallen_raindrops(self):
        old_number_of_raindrops = self.current_number_of_raindrops()
        self.raindrops = list(filter(self.raindrop_hit_the_ground, self.raindrops))
        self.raindrops_evaded += old_number_of_raindrops - self.current_number_of_raindrops()

    def raindrop_hit_the_ground(self, A):
        return A[1] == 0
    # [...]
```

#### Moving the player

We want the player to move along the x-axis, so we'll poll the keys and modify the player's x-component accordingly.

```python
# [...]
class AcidRain:
    # [...]
    def check_and_move_player(self):
        keys = pew.keys()
        x = self.player[0]
        dx = 0
        if keys & pew.K_LEFT:
            dx -= 1
        elif keys & pew.K_RIGHT:
            dx += 1

        if dx: # actual movement
            self.player = x+dx, self.player[1]
```

Although the above is logically correct, we haven't mitigated against _signal bounce_. You can read about _debouncing_ online, [here's an informative post you can read](http://www.ganssle.com/debouncing.pdf).

We'll handle debouncing using software. Thankfully, the authors of `qsnake.py` had a debouncing function in their code:

```python
def debounce():
    for i in range(100):
        pew.tick(1/100)
        if not pew.keys():
            return
```

Calling `debounce` after polling the keys for our game has the PewPew block if it detects any additional key presses for up to a second. Adding `debounce` as a method to the `AcidRain` class and calling it after polling the keys puts our code at:

```python
# [...]
class AcidRain:
    # [...]
    def check_and_move_player(self):
        keys = pew.keys()
        self.debounce()
        x = self.player[0]
        dx = 0
        if keys & pew.K_LEFT:
            dx -= 1
        elif keys & pew.K_RIGHT:
            dx += 1

        if dx: # actual movement
            self.player = x+dx, self.player[1]

    def debounce(self):
        for i in range(100):
            pew.tick(1/100)
            if not pew.keys():
                return
```

We'd like to add the possibility of 'wrapping around' the edges of the screen as a configurable game mod, so we'll define a flag `__WRAP_AROUND` and change our code to:

```python
# [...]
__SCREEN_MAX_X = const(7)
__SCREEN_MIN_X = const(0)
# Mods
__WRAP_AROUND = True

class AcidRain:
    # [...]
    def check_and_move_player(self):
        # [...]
        if x + dx > __SCREEN_MAX_X:
            dx = -7 if __WRAP_AROUND else 0
        if x + dx < __SCREEN_MIN_X:
            dx = 7 if __WRAP_AROUND else 0

        if dx: # actual movement
            self.player = x+dx, self.player[1]
```

#### Handling player collision

As the raindrops fall on the screen, we'd like to check if the player has been hit by any of them, and if so, the game would be over.

The PewPew's `pew` library has defined a `GameOver` exception. This is a fitting exception to raise when a raindrop hits our player, so we'll do so.

so we define:

```python
# [...]
class AcidRain:
    # [...]
    def check_for_player_collision(self):
        if any(self.player == raindrop for raindrop in self.raindrops):
            raise pew.GameOver
    # [...]
```

#### Rendering our game

To render a single pixel to a PewPew's screen, we need to call two methods: `pew.Pix.pixel` and `pew.show`.

`pew.Pixel.pixel` requires a coordinate-pair x and y, as well as a color argument. The color is an `int` representing the intensity: it's between 0 and 255. When supplied these, `pew.Pix.pixel` modifies an internal buffer with the supplied modifications, but doesn't actually render them to the screen.

For that, we require `pew.show`, which requires a `pew.Pix` object, and actually renders the internal buffer's content on the 8x8 screen.

##### Initial approach

Making use of `self.screen.pixel` calls whenever a pixel needs to be created on the screen such as when we generate raindrops or move the player seemed cumbersome. We'd have to keep track of multiple calls and make sure that they're always called, and this 'felt annoying' (read 'programmer was uncomfortable maintaining the code').

We wish to adopt a more centralised approach to modifying the elements on-screen.

##### Keeping track of objects to draw and erase

We opt for two lists: `self.to_draw` and `self.to_erase`. Either will contain the coordinates of objects that need to be drawn and erased respectively.

This allows the calls to `pew.Pix.pixel` and `pew.show` to be centralised, and seems neater. However this also means that objects to be drawn (raindrops, the player) and erased (fallen/falling raindrops, player's previous positions) need to be updated into the lists.

We highlight this by rewriting `AcidRain.update_raindrops` as an example:

```python
# [...]
class AcidRain:
    def __init__(self):
        # [...]
        self.to_draw = []
        self.to_erase = []
        # [...]
    # [...]
    def update_raindrops(self):
        for i in range(len(self.raindrops)):
            self.to_erase.append(self.raindrops[i])
            self.raindrops[i] = (self.raindrops[i][0], self.raindrops[i][1] + 1)
            self.to_draw.append(self.raindrops[i])
    # [...]
```

#### Implementing `run_game`

`AcidRain.run_game` is the game's main control loop. We envision the game being run by placing a single call to `AcidRain.run_game` within a permanent loop.

Apart from actually running the game, this means that the method will have to display the title screen as well as the game-over screen complete with the player's score after having actually ran the game.

##### Title and game-over screens

We can handle both of these tasks as follows:

```python
# [...]
class AcidRain:
    def __init__(self):
        # [...]
        self.raindrops_evaded = 0
        # Visuals
        self.title = pew.Pix.from_text("AcidRain")
        self.game_over = pew.Pix.from_text("Game Over!")
    # [...]
    def run_game(self):
        # Title
        game_started = False
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
            # INSERT GAME LOGIC HERE
        except pew.GameOver:
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

    def check_for_start(self):
        keys = pew.keys()
        return keys & pew.K_O or keys & pew.K_X
    def clear_screen_for_start(self):
        self.screen.box.(0, x=0, y=0, width=8, height=8)
```

We're calling `pew.Pix.blit` with a `pew.Pix` (`self.title` and `self.game_over`), and 2 integers (`-dx` and `1`).

The method efficiently copies a `pew.Pix`'s `buffer` (`self.title.buffer` or `self.game_over.buffer`) content into another `pew.Pix`'s buffer (`self.buffer`).

The 2 integers are the values of the keyword arguments `dx` and `dy`, integers by which the content to copy will be shifted by in the x and y directions respectively.

We make the choice to start the game by pressing either the O or X buttons, so `AcidRain.check_for_start` returns `True` if either key was pressed.

`self.screen.box(0, x=0, y=0, width=8, height=8)` fills `self.buffer` with a `width`-by-`height` box of color `0` starting at (x,y) = (0,0), effectively clearing the screen.

`pew.tick` takes a delay in seconds as its single argument and sleeps for that amount of time. We call it to ensure a consistent refresh rate for the screen (an optimal gaming experience), otherwise the LEDs would light up and shut off as fast as the PewPew can execute our code, which is far too quick both for us to perceive and for the LEDs to act.

##### Game logic

Inside the space left for the game logic, we need to update game variables, render new objects and erase old ones, keep score, poll keys, etc. Having already modularly implemented all of those features above, `AcidRain.run_game` turns into an orchestrative method. We need only carefully consider the order in which we'll call all of our defined methods.

Note that the order in which we execute code (particularly `AcidRain.check_for_player_collision` and when we draw objects) has a noticeable effect on gameplay (try it out!).

```python
# [...]
class AcidRain:
    # [...]
    def run_game(self):
        # Title
        # [...]
        try:
            while True:
                self.check_and_move_player()
                self.remove_fallen_raindrops()
                self.update_raindrops()
                self.generate_new_raindrops()
                self.check_for_player_collision()
                # Update screen elements here
                while len(self.to_erase):
                    self.screen.pixel(*self.to_erase.pop(0), color=0)
                while len(self.to_draw):
                    self.screen.pixel(*self.to_draw.pop(0), 255)
                # Show updated screen
                pew.show(self.screen)
        except pew.GameOver:
            # [...]
    # [...]
```

However, as the code stands the game would just run too quickly for us to play and we'd reach the game-over screen instantly. We need to make a call to `pew.tick` to ensure a consistent refresh rate. For this, let's also define `self.game_speed` and `self.speed_factor`.

The thought behind game speed progression wasn't well developed, so the game speed gets multiplied by a constant slightly higher than one (geometric sequence tending to positive infinity) at every iteration of the `while True` loop.

This makes the game refresh quicker as time goes on, and thus simulate an increase of the speed at which raindrops fall to the ground. It also means that the game speed grows at an exponential rate, so the game will be impossible to play after a few iterations. We won't worry about that for now.

```python
# [...]
__STARTING_SPEED = const(2)

class AcidRain:
    def __init__(self):
        # [...]
        # Game stats
        # [...]
        self.game_speed = __STARTING_SPEED
        self.speed_factor = 1.012
    # [...]
    def run_game(self):
        # Title
        # [...]
        try:
            while True:
                # [...]
                # Show updated screen
                pew.show(self.screen)
                pew.tick(1/self.game_speed)
                self.game_speed *= self.speed_factor
        except pew.GameOver:
            # [...]
```

We now have a functional game!

##### Cosmetic change

At the moment we are drawing both the player and the raindrops with the same color. We wish to draw the player in brightest red and the raindrops in a fainter red, so we'll refrain from adding the player from `self.to_draw` and `self.to_erase` and draw/erase them from `AcidRain.run_game`.

```python
# [...]
__DRAWING_COLOR = const(1)
__ERASING_COLOR = const(0)
__PLAYER_COLOR = const(255)
#[...]

class AcidRain:
    # [...]
    def run_game(self):
        # [...]
        try:
            self.screen.pixel(*self.player, color=__ERASING_COLOR)
            self.check_and_move_player()
            self.screen.pixel(*self.player, color=__PLAYER_COLOR)
            # [...]
            # Update screen elements here
            while len(self.to_erase):
                self.screen.pixel(*self.to_erase.pop(0), color=__ERASING_COLOR)
            while len(self.to_draw):
                self.screen.pixel(*self.to_draw.pop(0), color=__DRAWING_COLOR)
            # [...]
        except pew.GameOver:
            # [...]
    # [...]
```

#### Adding the quantum element

We now make use of MicroQiskit in our code. We make the following modifications:

```python
from micropython import const
from microqiskit import QuantumCircuit, simulate
import pew

qc = QuantumCircuit(1,1)
qc.h(0)
qc.measure(0,0)

def randGen():
    digits = []
    for _ in range(3):
        counts = simulate(qc, shots=1, get='memory')
        digits += counts

    BinString = ''.join(digits)

    BinNum = int(BinString, 2)

    return BinNum

# [...]

class AcidRain:
    # [...]
    def new_raindrop(self):
        return randGen(), __STARTING_Y
```

`qc = QuantumCircuit(1,1)` intialises a quantum circuit with 1 qubit and 1 output bit. `qc.h(0)` adds a Hadamard gate to the single qubit at position 0. The Hadamard gate is what let's us use the value of the qubit to represent a fair coin toss by giving either state (0 or 1) an equal probability. `qc.measure(0,0)` reads out qubit 0 into output bit 0.

The `simulate` function simulates our experiment (currently applying a Hadamard gate and reading the output state): `shots` dictates the amount of times to simulate the experiment, `get` decides the format in which we want the result of the experiment.

With `get=memory`, `simulate` returns a list containing `shots` strings, each either `"0"` or `"1"`. We join these strings together and turn them into an integer using the `int` function and specifying base 2.

#### Quantum tunnelling

##### Initial implementation

As per a Qiskit advocate's suggestion, what if we added 'quantum tunnelling' to our game?

If a raindrop were directly above the player, pressing up would initiate a coin toss deciding whether or not the player 'passes through the raindrop' (survives) or collides with the raindrop and dies.

To make the game more enticing, we decided to have a 50-50 coin toss decide the player's outcome.

The decision to allow for quantum tunnelling can only begin if an up-key press has been detected. Once more the theme is centralisation, so we'll check for an up-key press in the only place where our code polls the PewPew's keys: `AcidRain.check_and_move_player`.

```python
# [...]
class AcidRain:
    # [...]
    def check_and_move_player(self):
        # [...]
        if keys & pew.K_UP:
            self.handle_quantum_tunnelling()
        else:
            if keys & pew.K_LEFT:
                dx -= 1
            elif keys & pew.K_RIGHT:
                dx += 1
            # [...]
    # [...]

    def handle_quantum_tunnelling(self):
        if any(self.raindrop_is_above_position(raindrop, self.player) for raindrop in self.raindrops):
            raindrop_above = self.player[0], self.player[1]-1
            if randGen() <= 3:
                if any(self.raindrop_is_above_position(raindrop, raindrop_above) for raindrop in self.raindrops):
                    raise pew.GameOver
                else:
                    self.to_erase.append(raindrop_above)
                    self.raindrops = list(filter(lambda x: x != raindrop_above), self.raindrops)
            else:
                raise pew.GameOver

    def raindrop_is_above_position(self, A, B):
        return A[0] == B[0] and A[1] == B[1] - 1
```

In `AcidRain.handle_quantum_tunnelling`, the first if-statement checks if any raindrops are directly above the player: if not, nothing happens.

Otherwise we then check if the coin toss resulted in the player dying or not: we choose `randGen()` being less than 3 to represent success, yielding a 50-50 probability split. If `randGen() > 3` then we raise a `pew.GameOver` exception. If the coin toss is in the player's favour, we'll check if there is another raindrop immediately above the raindrop above the player, in which case quantum tunnelling will send the player straight into another raindrop and kill them (we don't want quantum tunnelling to surpass the distance of a single raindrop).

If there isn't a raindrop directly above the one above the player, we'll add the raindrop above the player to the list of game elements to erase, as well as remove it from the list of raindrops. This simulates travelling through the raindrop.

##### Second implementation

As per another Qiskit advocate's suggestion, what if the probabilistic element of the quantum tunnelling feature mimicked the actual physical probability?

After looking up [a Wikipedia page](https://en.wikipedia.org/wiki/Rectangular_potential_barrier), an initial implementation was made:

```python
from math import sin, cos
from micropython import const
from microqiskit import QuantumCircuit, simulate
import pew

# [...]
__PLANCK = 6.626e-34
__V_ZERO = __STARTING_SPEED

def comp_exp(comp):
    return cos(comp) + 1j*sin(comp)

class AcidRain:
    # [...]
    def handle_quantum_tunnelling(self):
        if any(self.raindrop_is_above_position(raindrop, self.player) for raindrop in self.raindrops):
            raindrop_above = self.player[0], self.player[1]-1

            a = 1
            m = 1
            E = self.game_speed**2/2
            k_0 = sqrt(2*m*E/__PLANCK**2)
            k_1 = sqrt(2*m*(E-__V_ZERO)/__PLANCK**2)

            t = 4*k_0*k_1*comp_exp(-1*a*(k_0-k_1))
            t /= (k_0+k_1)**2 - comp_exp(2*a*k_1)*(k_0 - k_1)**2

            if randGen()/7 <= t:
                # [...]
            else:
                raise pew.GameOver
    # [...]
```

`comp_exp` was defined to evaluate `exp` for complex arguments using Euler's formula. This proved to be too costly memory-wise for the PewPew and had to be simplified, `sqrt` and `comp_exp` being the main offenders.

Plotting the probability `t` as a function of `E` revealed that for our chosen `__V_ZERO` we obtain a function that maxes out fairly early, which also required some modifications to our code, which I've just noticed to be erroneous in the actual code (quantum tunnelling is practically always possible).

## After the hackathon

### Weaknesses

#### `AcidRain.handle_quantum_tunnelling`

Erroneous and could be better.

#### `AcidRain.debounce`

As a fellow hacker demonstrated, constantly holding any of the PewPew's buttons slowed the game down to a leisurely pace, although releasing it saw the game speed burst.

The issue comes from the `debounce` method I took from `qsnake.py`, a quantum implementation of Snake.

```python
class AcidRain:
    # [...]
    def debounce(self):
        for i in range(100):
            pew.tick(1/100)
            if not pew.keys():
                return
    # [...]
```

`AcidRain.debounce` is called after every key sampling and incurs a `1/100 * 100 = 1` second delay if a _bounce_ is detected. Holding down any key results in a bounce and thus the game slowing down.

#### Memory consumption

The PewPew does not have enough memory to run both the game and compute a physically accurate probability for quantum tunnelling.

More efficient code, most likely in the form of a non-OO approach, would probably give us this gratuitous but desirable feature.

### Future changes

#### `randGen`

`randGen` can be:

```python
# [...]

qc = QuantumCircuit(1,1)
qc.h(0)
qc.measure(0,0)

def randGen():
    return int(''.join(*simulate(qc, shots=3, get='memory')), 2)
```

#### Cleaning up unused variables/imports

We can remove remnant, unused imports from last minute hacking. Turning

```python
from math import sin, cos
from micropython import const
from microqiskit import QuantumCircuit, simulate
from time import sleep
import pew
```

into

```python
from micropython import const
from microqiskit import QuantumCircuit, simulate
import pew
```

We can also remove unused variables which were the result of last-minute hacking and overlapping implementations of different ideas.

- `self.old_player` in `AcidRain.__init__`
- `a` and `m` in `AcidRain.handle_quantum_tunnelling`

### Improved game

Coming in the near future (soon).
