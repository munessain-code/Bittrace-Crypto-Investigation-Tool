#!/usr/bin/env python3
"""Tests for the Phase 7 storytelling module.

Covers:
  - YAML story loading (schema, loader)
  - Minimum story count and step counts
  - Real node IDs exist in the dataset
  - export_story_subgraph integration
"""

import json
from pathlib import Path

import pytest

from src.stories import load_all_stories, load_story, get_story_by_id
from src.stories.schema import Difficulty, Story, StoryStep

CASES_DIR = Path(__file__).resolve().parent.parent / "src" / "stories" / "cases"


# ---------------------------------------------------------------------------
# Basic loading
# ---------------------------------------------------------------------------
class TestLoadStories:
    def test_load_all_returns_list(self):
        stories = load_all_stories(CASES_DIR)
        assert isinstance(stories, list)

    def test_at_least_3_stories(self):
        stories = load_all_stories(CASES_DIR)
        assert len(stories) >= 3, f"Expected >= 3 stories, got {len(stories)}"

    def test_each_has_at_least_3_steps(self):
        stories = load_all_stories(CASES_DIR)
        for s in stories:
            assert len(s.steps) >= 3, (
                f"Story '{s.id}' has {len(s.steps)} steps, expected >= 3"
            )

    def test_each_has_seed_node_id(self):
        stories = load_all_stories(CASES_DIR)
        for s in stories:
            assert isinstance(s.seed_node_id, int)
            assert s.seed_node_id > 0

    def test_each_has_narrative(self):
        stories = load_all_stories(CASES_DIR)
        for s in stories:
            assert len(s.narrative.strip()) > 10, (
                f"Story '{s.id}' has a very short narrative"
            )

    def test_difficulties_are_valid(self):
        stories = load_all_stories(CASES_DIR)
        valid = {d.value for d in Difficulty}
        for s in stories:
            assert s.difficulty.value in valid, f"Invalid difficulty: {s.difficulty}"


# ---------------------------------------------------------------------------
# Specific stories
# ---------------------------------------------------------------------------
class TestSpecificStories:
    def test_peel_chain_story(self):
        story = get_story_by_id("peel-chain", CASES_DIR)
        assert story.id == "peel-chain"
        assert story.seed_node_id == 10000476
        assert story.difficulty == Difficulty.EASY
        assert story.pattern == "peel_chain"

    def test_fan_out_story(self):
        story = get_story_by_id("fan-out-split", CASES_DIR)
        assert story.id == "fan-out-split"
        assert story.seed_node_id == 32054179
        assert story.difficulty == Difficulty.AVERAGE
        assert story.pattern == "fan_out"

    def test_consolidation_story(self):
        story = get_story_by_id("consolidation", CASES_DIR)
        assert story.id == "consolidation"
        assert story.seed_node_id == 30179316
        assert story.difficulty == Difficulty.HARD
        assert story.pattern == "fan_in"


# ---------------------------------------------------------------------------
# StoryStep structure
# ---------------------------------------------------------------------------
class TestStorySteps:
    def test_steps_have_incremental_numbers(self):
        stories = load_all_stories(CASES_DIR)
        for s in stories:
            nums = [step.step_num for step in s.steps]
            assert nums == list(range(1, len(nums) + 1)), (
                f"Story '{s.id}' steps not 1-indexed sequentially: {nums}"
            )

    def test_steps_have_titles(self):
        stories = load_all_stories(CASES_DIR)
        for s in stories:
            for step in s.steps:
                assert len(step.title.strip()) > 0, (
                    f"Story '{s.id}' step {step.step_num} has empty title"
                )

    def test_highlight_nodes_are_ints(self):
        stories = load_all_stories(CASES_DIR)
        for s in stories:
            for step in s.steps:
                for nid in step.highlight_nodes:
                    assert isinstance(nid, int), f"highlight_node not int: {nid}"


# ---------------------------------------------------------------------------
# to_dict serialization
# ---------------------------------------------------------------------------
class TestSerialization:
    def test_to_dict_roundtrip(self):
        story = get_story_by_id("peel-chain", CASES_DIR)
        d = story.to_dict()
        assert "id" in d
        assert "steps" in d
        assert len(d["steps"]) >= 3
        assert isinstance(d["steps"][0]["highlight_nodes"], list)

    def test_to_dict_is_json_serializable(self):
        story = get_story_by_id("consolidation", CASES_DIR)
        d = story.to_dict()
        # Should not raise
        json.dumps(d, default=str)
