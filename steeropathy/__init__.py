"""steeropathy — one agent's mood, poured into another. No words, just a vector."""

# Import the submodules (not their same-named functions) so `steeropathy.transmit`
# and `steeropathy.offer` stay the MODULES — importing the functions here would
# shadow the submodules and break `from . import transmit` inside the package.
from . import offer, transmit
from .offer import OFFERS
from .transmit import MOODS

__all__ = ["transmit", "offer", "MOODS", "OFFERS"]
