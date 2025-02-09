A fork of cq-editor with support for selectable dark+light colour theme added. Also, an optional switch to delete the saved preferences from disk was added due to reasons. I started the fork out of simple need, as cq-editor + cadquery look very promising for some ideas I have -  e.g. programmatically generated, parametrically comprehensive 3D models of inductor coils for use with KiCAD - at the same time that light backgrounds are unusable for me together with the dark ones I'm used to (actually they feel like a bright brick wall slamming into the visual cortex).  

Some of the ways my changes accomplish things may be inelegant, break the OO paradigm or in other ways be abominable, due to (but probably not exclusively):

1. This is the first time I use conda (I settled for micromamba).
2. This is the first time I make changes in any Python code I didn't write myself the same week.
3. This is the third time I do anything in Python except for a page-long text processing hack two years ago and a similar one five years ago.
4. This is the first time I do anything using the qt framework aside from a 'hello world' window sometime around the previous millenium.
5. This is the first time I use git for anything more esoteric than 'git clone'.

It wasn't until I was done with the goal I had set that I was struck with the realization that there's a non-negligible probability that my dark mode implementation may be of use to someone, and that the socially responsible thing to do would be to publizise my work on github. Hence (5) above, in addition to, as a result of me from the outset only planning to risk myself being exposed to my code:

6. Any documentation in the commit is what I remember after everything was done, which is probably half if that.

The largest (only...?) difference between the conda environment dependencies in my fork w.r.t. the origin is a Python version bump to 3.10.? and the resulting versions upgrades of everything dependant on it. I probably didn't have good reasons, although I do remember something about a non-ancient qdarkstyle version and its requirements, although I may be confusing it with something else that may or may not be reality-related. Additionally, there may well remain unnecessary and forgotten packages I installed but ultimately didn't need.

The steps to get my code running are something at least similar to the ones below:

$ cd ~/
$ wget -qO- https://micromamba.snakepit.net/api/micromamba/linux-64/latest | tar -xvj bin/micromamba
$ bin/micromamba shell init -s bash -p ~/micromamba

$ git clone https://github.com/axhan/CQ-editor_themed.git
$ micromamba env create -f CQ-editor/cqgui_env.yml -n cqgui
$ micromamba activate cqgui
(cqgui) $ cd ~/micromamba/envs/cqgui

(cqgui) $ micromamba install python=3.10.4 -c conda-forge
(cqgui) $ micromamba install cadquery=master -c CadQuery
(cqgui) $ micromamba install spyder -c conda-forge

(cqgui) $ mkdir src
(cqgui) $ mv ~/CQ-editor src/
(cqgui) $ cd src/CQ-editor

# Test run:
(cqgui) $ python run.py

![Screenshot from 2022-04-08 16-18-39](https://user-images.githubusercontent.com/41844315/162455097-620813fb-4279-4013-a9d1-e7f3aaed12ab.png)
![Screenshot from 2022-04-08 16-18-55](https://user-images.githubusercontent.com/41844315/162455138-97051129-ad2f-48ca-94c7-b9316d37456a.png)
