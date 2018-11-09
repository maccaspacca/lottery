# A Bismuth Blockchain Based Lottery

This repository contains the code for a Bismuth blockchain based lottery.

## How it works

1. The players send 1 Bismuth per entry to the Bismuth lottery address including the text "lotto:enter" in the operation field

2. At the end of each lottery round the software checks for valid entries and selects first, second and third place winners

3. It then sends the prizes to each winner and sets the block number for the end of the next round

4. The parameters of the lottery can be changed in the "lottery.ini" file which is annotated

5. The software is intended to run against a local node but can run against the Bismuth API wallet servers

## Installation

1. Install the python prerequisites into your Python 3.6 installation (see requirements.txt)

2. Place the files into a suitable folder.

3. Adjust the lottery.ini file as needed

## How to Run

4. Run the software e.g. "python lprocs.py"

5. If you run the software before the end of the round, it will run a simulation only if there are more than 3 entries

6. If you run the software after the end of a round it will select the winners, pay them and set the block number for the end of the next round
