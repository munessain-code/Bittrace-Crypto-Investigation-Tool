#!/usr/bin/env python3
"""YAML loader for BitTrace investigation stories.

Stories live in ``src/stories/cases/*.yaml``. Each file defines one
Story with steps, highlights, and narrative text.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

import yaml

from src.stories.schema import Difficulty, Story, StoryStep

logger = logging.getLogger(__name__)

# Default cases directory (relative to this file)
_CASES_DIR = Path(__file__).resolve().parent / "cases"


def _load_story_from_dict(
    data: Dict,
    source_file: str = "",
) -> Story:
    """Convert a YAML-parsed dict into a Story dataclass."""
    raw_steps = data.get("steps", [])
    steps = []
    for s in raw_steps:
        steps.append(
            StoryStep(
                step_num=s["step_num"],
                title=s["title"],
                description=s["description"],
                highlight_nodes=s.get("highlight_nodes", []),
                highlight_edges=s.get("highlight_edges", []),
                trace_direction=s.get("trace_direction", "downstream"),
            )
        )

    return Story(
        id=data["id"],
        title=data["title"],
        difficulty=Difficulty(data["difficulty"]),
        seed_node_id=int(data["seed_node_id"]),
        pattern=data.get("pattern", "unknown"),
        narrative=data.get("narrative", ""),
        steps=steps,
        source_file=source_file,
    )


def load_story(yaml_path: str) -> Story:
    """Load a single story from a YAML file.

    Args:
        yaml_path: Absolute or relative path to the ``.yaml`` file.

    Returns:
        Parsed :class:`Story`.
    """
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Story file not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    logger.info("Loaded story '%s' from %s", data.get("id", "?"), path)
    return _load_story_from_dict(data, source_file=str(path))


def load_all_stories(cases_dir: str | Path | None = None) -> List[Story]:
    """Load every ``.yaml`` / ``.yml`` story in the cases directory.

    Args:
        cases_dir: Override the default cases directory.

    Returns:
        List of :class:`Story`, sorted by difficulty then id.
    """
    cases = Path(cases_dir) if cases_dir else _CASES_DIR
    if not cases.exists():
        raise FileNotFoundError(f"Cases directory not found: {cases}")

    stories: List[Story] = []
    for yaml_file in sorted(cases.glob("*.yaml")) + sorted(cases.glob("*.yml")):
        try:
            story = load_story(str(yaml_file))
            stories.append(story)
        except Exception as e:
            logger.warning("Failed to load %s: %s", yaml_file, e)

    difficulty_order = {"EASY": 0, "AVERAGE": 1, "HARD": 2}
    stories.sort(key=lambda s: (difficulty_order.get(s.difficulty.value, 3), s.id))

    logger.info("Loaded %d stories from %s", len(stories), cases)
    return stories


def get_story_by_id(story_id: str, cases_dir: str | Path | None = None) -> Story:
    """Find and return a single story by its ``id`` field.

    Raises:
        KeyError: If no story with the given id is found.
    """
    all_stories = load_all_stories(cases_dir)
    for s in all_stories:
        if s.id == story_id:
            return s
    raise KeyError(
        f"Story '{story_id}' not found among {[s.id for s in all_stories]}"
    )
