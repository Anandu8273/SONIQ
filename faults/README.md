# Controlled fault injection for later demo phases.

Do not give SONIQ the injected fault. Evaluation reads `evaluation/ground_truth.json`.

Future injection ideas (manual / operator-controlled only):

- Interface error / CRC increment simulation on a leaf
- Packet loss via traffic control in the virtual topology
- BGP session shutdown (human-approved, not agent-initiated)

SONIQ must observe the network afterward with read-only tools.
