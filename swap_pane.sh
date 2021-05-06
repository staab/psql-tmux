#!/bin/bash

tmux split-pane -d "$@"
tmux select-pane -D

