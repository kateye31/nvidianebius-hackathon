# Safety and privacy

- The device never touches mains. Grid sensing uses a cut USB cable from a
  5 V phone charger into a 1:2 resistor divider (1k/2k or 10k/20k) to GPIO26.
  Cut the cable, never the charger; never open anything plugged into a wall.
- ESP32 pins take 3.3 V max: the HC-SR04 echo also goes through a divider.
- The relay switches only low-voltage loads on a powerbank in the demo.
- Never run a generator indoors or create CO for testing. The "generator
  suspected" flag is a heuristic and is labeled as such.
- Nobody photographs or approaches downed lines for this project.
- Nightlight recommends; a human dispatcher approves every action.
- Stored per home: unit id, approximate location, occupants count, a
  medical-load yes/no flag. No names, diagnoses, or exact addresses.
