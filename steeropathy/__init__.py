"""steeropathy — agents that communicate through what they never generate.

No text passes between them: they read each other's internal state (activations,
and the words forming in the layers that never become tokens) and can push a vector
straight into another's next forward pass. Feeling is just the first payload we send
through the channel. A playground of experiments — transmit, offer, ecosystem,
resonance — meant to be run, and extended.
"""

# Import the submodules (not their same-named functions) so `steeropathy.transmit`
# and `steeropathy.offer` stay the MODULES — importing the functions here would
# shadow the submodules and break `from . import transmit` inside the package.
from . import offer, transmit
from .offer import OFFERS
from .transmit import MOODS

__all__ = ["transmit", "offer", "MOODS", "OFFERS"]
