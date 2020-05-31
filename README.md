# CATOS
 Software to work with multiple sensors and actuators via Arduino to run training/experimental session with animal subjects.

Jinook Oh, Cognitive Biology department, University of Vienna<br>
Contact: jinook0707@gmail.com, tecumseh.fitch@univie.ac.at<br>
May 2020.

## Dependency:
- **Python** (3.7)
- **wxPython** (4.0)
- **numPy** (1.15)
- **OpenCV** (4.1)
- **pySerial** (3.4)
- (**PyOpenAL**)

## Note
This software was used in 2016 to train/test common marmoset monkeys, <br>
using an arena equipped with three surrounding screens (one touch-screen and two normal screens on each side), three webcams to watch the frontal area of each screen, an automatic feeder[1], and 5.1 channel speakers also surrounding the arena.<br>

Its goal was to draw attention of monkeys with moving circles. The circles were designed to change its size and randomly moves around while sticking together as a group to imitate a group flies flying around. The circles moved across three screens and when a subject was detected close to a side screen, the circles moved to the middle screen. When a subject touched the circles, hovering in the middle screen, the automatic feeder released a piece of food to reinforece the behaviour of touching visual stimulus.<br>

when a subject touches the area of circles moving around, 
It was coded to use the specific design of the arena, and its current state is not suitable for using it for other training/experiments as it is.
However, this is uploaded to a repository in 2020 for the purpose of sharing pieces of code with coleagues.<br>
It will be updated when it's developed in more generalized and structured form.<br>

[1] Oh, J., Hofer, R., & Fitch, W. T. (2017). An open source automatic feeder for animal experiments. HardwareX, 1, 13-21.
https://www.sciencedirect.com/science/article/pii/S2468067216300050?via%3Dihub
