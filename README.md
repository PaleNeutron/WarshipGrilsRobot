# WarshipGrilsRobot
a Robot for warship grils.
You can create self-designed robot script to resolve warshipgirls daily work.

## Requirement
1. Python 3
2. requests
3. transitions

## Usage
The version is an alpha version, classes you need is in `zrobot.py` and `zemulator.py`.

japan_server.py is an example

You can define your own mission by inherit `zrobot.Mission`.
And then put it in `zrobot.Robot` class. There is a state machine in the robot, so it can resolve all missions automatically.
