## Summary
<!-- brief summary of the repository -->
This repository contains the source code for comma AI's ADAS software Openpilot. It is an open-source driving agent that uses a dashcam to provide autonomous driving capabilities utilizing the car's LKAS, ACC, and other systems. I am using the repository as a starting point for developing my own project that aims to adjust the passenger seat position based on the imminent vehicle motion in order to enhance passenger comfort.

## Terminology
<!-- list of domain specific terms with their explanation -->
- LKAS: Lane Keeping Assist System, a feature that helps the driver keep the vehicle centered in its lane.
- ACC: Adaptive Cruise Control, a system that automatically adjusts the vehicle's speed to maintain a safe distance from the car in front.
- sunnypilot: An experimental fork of openpilot that adds new features and utilizes openpilot capabilities that are not yet available in the main branch.
- frogpilot: Another experimental fork of openpilot that focuses on enhancing the driving experience through additional features and improvements.
- capnp: A data interchange format used in openpilot for efficient serialization and deserialization of data structures.
- msync: The company I work for, which is developing the seat control system. It is an abbreviation of "Motion Sync".
- ModelV2: The neural network openpilot uses for predictions about the future vehicle state.
- ModelDataV2: The data produced by ModelV2, which includes predictions about the vehicle's future state.
- LongitudinalPlan: The x axis component of the planned vehicle trajectory over the next 2.5 seconds.

## Architecture
<!-- short summary of the architecture -->
The  architecture consists of several modular components including:
- `/cereal/`: Contains the messaging system used for communication between openpilot's modules.
- `/selfdrive/`: Contains the main driving agent logic, including the neural networks and car control algorithms.
- `/tools/`: Contains various tools and utilities for developing and testing openpilot, including replay features and logging tools.
- `/sunnypilot_dev_msync/`: Contains the source code I have written to modify and utilize openpilot.
- `/sunnypilot/`: Contains the source code for the modifications in the sunnypilot fork.
- `log.capnp`: Contains the Cap'n Proto schema for all message events and most of the message definitions.
- `car.capnp`: Contains the Cap'n Proto definitions for car-specific messages.
- `custom.capnp`: Contains the Cap'n Proto definitions for custom messages defined by me or by sunnypilot developers.
- `short_control.py`: A file that contains the logic for controlling the passenger seat based on the predicted and current motion.


## Task planning and problem-solving
<!-- the most important problem-solving guidelines -->
<!-- e.g. "plan the task before writing any code" -->
- Before writing code, follow these steps:
  1. Understand the problem and requirements. Ask clarifying questions if needed.
  2. Provide a full plan of your changes.
  3. Provide a list of behaviors you will modify.
- After writing code, follow these steps:
  1. Ensure the code is well-documented and follows the coding guidelines.
  2. Make sure existing code is re-used where possible.
- When searching the codebase, consider the following:
  1. Files that end in an extra "d" are usually daemon files that send messages.
  2. There are some instances where the same file is defined with a c++ extension and a python extension. In these instances, the c++ file is usually the one that actually runs on launch, and the python files are more often used for testing or development purposes.
  3. Many directories contain README's. Read them to get hints about what files are important and how they interact.