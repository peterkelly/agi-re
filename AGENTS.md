# AGENTS.md

## Summary

This is a project to perform a clean room reverse engineering of AGI (Adventure Game Interpreter), a game engine created by Sierra on-line in the 1980s.

This effort uses the game Space Quest 2 (located in the SQ2 directory).

While others have reverse engineered AGI before and there is plenty of documentation and source code available online, in this project we are explicitly not consulting any existing materials. This is an experiment to explore the reverse engineering capabilities of Codex, and using existing documentation or source code would work against that goal.

The output of this project is a human-readable spec that contains sufficient information to use another AI agent to do a clean-room implementation of AGI.

## Rules

- Do not make use of external documentation, source code, or your own training data about AGI
- Every step in the reverse engineering process must be documented, as proof that this is clean-room
