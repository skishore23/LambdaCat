"""Tests for agent entities system."""

import json
import tempfile
from pathlib import Path

import pytest

from src.LambdaCat.agents.actions import Task, sequence
from src.LambdaCat.agents.cognition.memory import AgentState
from src.LambdaCat.agents.core.bus import Message, MessageBus
from src.LambdaCat.agents.entities import (
    Goal,
    Intention,
    SimpleBus,
    SimpleIntentionPolicy,
    create_agent_entity,
    create_simple_bus,
    run_multi_agent_system,
)


class TestGoalAndIntention:
    """Test Goal and Intention classes."""

    def test_goal_creation(self):
        """Test goal creation with parameters."""
        goal = Goal(
            name="answer_query",
            params={"query": "What is AI?", "max_length": 100},
            priority=0.8,
            deadline=3600.0
        )

        assert goal.name == "answer_query"
        assert goal.params["query"] == "What is AI?"
        assert goal.priority == 0.8
        assert goal.deadline == 3600.0
        assert goal.constraints == {}

    def test_intention_creation(self):
        """Test intention creation with plan."""
        goal = Goal(name="test_goal", params={})
        plan = sequence(Task("test_task"))

        intention = Intention(
            goal=goal,
            plan_ast=plan,
            confidence=0.9,
            metadata={"source": "test"}
        )

        assert intention.goal == goal
        assert intention.plan_ast == plan
        assert intention.confidence == 0.9
        assert intention.metadata["source"] == "test"

    def test_intention_evaluation(self):
        """Test intention evaluation."""
        goal = Goal(name="test_goal", params={})
        plan = sequence(Task("test_task"))

        def evaluator(context: dict) -> float:
            return context.get("score", 0.5)

        intention = Intention(
            goal=goal,
            plan_ast=plan,
            evaluator=evaluator
        )

        # Test with evaluator
        score = intention.evaluate({"score": 0.8})
        assert score == 0.8

        # Test without evaluator
        intention_no_eval = Intention(goal=goal, plan_ast=plan)
        score = intention_no_eval.evaluate({})
        assert score == 1.0  # default confidence


class TestSimpleIntentionPolicy:
    """Test SimpleIntentionPolicy."""

    def test_policy_creation(self):
        """Test policy creation."""
        goal_to_plan = {"test_goal": sequence(Task("test_task"))}
        policy = SimpleIntentionPolicy(goal_to_plan, default_confidence=0.7)

        assert policy.goal_to_plan == goal_to_plan
        assert policy.default_confidence == 0.7

    def test_propose_intentions(self):
        """Test intention proposal."""
        goal_to_plan = {"answer_query": sequence(Task("search"), Task("synthesize"))}
        policy = SimpleIntentionPolicy(goal_to_plan)

        goals = [
            Goal(name="answer_query", params={"query": "test"}),
            Goal(name="unknown_goal", params={})
        ]

        state = AgentState()
        context = {}

        intentions = policy.propose_intentions(goals, state, context)

        # Should only propose intention for known goal
        assert len(intentions) == 1
        assert intentions[0].goal.name == "answer_query"
        assert intentions[0].confidence == 0.8  # default

    def test_select_action(self):
        """Test action selection."""
        policy = SimpleIntentionPolicy({})

        goal1 = Goal(name="goal1", params={})
        goal2 = Goal(name="goal2", params={})
        plan = sequence(Task("test"))

        intentions = [
            Intention(goal=goal1, plan_ast=plan, confidence=0.6),
            Intention(goal=goal2, plan_ast=plan, confidence=0.9)
        ]

        selected = policy.select_action(AgentState(), intentions, {})

        # Should select highest confidence
        assert selected.goal.name == "goal2"
        assert selected.confidence == 0.9


class TestAgentEntity:
    """Test AgentEntity class."""

    @pytest.fixture
    def mock_skills(self):
        """Mock skills for testing."""
        async def skill1(state: dict, ctx: dict) -> dict:
            return {**state, "skill1_result": "done"}

        def skill2(state: dict, ctx: dict) -> dict:
            return {**state, "skill2_result": "done"}

        return {"skill1": skill1, "skill2": skill2}

    @pytest.fixture
    def agent_entity(self, mock_skills):
        """Create a test agent entity."""
        goals = [Goal(name="test_goal", params={"test": "value"})]
        goal_to_plan = {"test_goal": sequence(Task("skill1"), Task("skill2"))}
        bus = MessageBus()

        return create_agent_entity(
            agent_id="test_agent",
            goals=goals,
            skills=mock_skills,
            goal_to_plan=goal_to_plan,
            bus=bus
        )

    def test_agent_creation(self, agent_entity):
        """Test agent entity creation."""
        assert agent_entity.aid == "test_agent"
        assert len(agent_entity.goals) == 1
        assert agent_entity.goals[0].name == "test_goal"
        assert not agent_entity.running

    def test_goal_management(self, agent_entity):
        """Test goal management methods."""
        # Add goal
        new_goal = Goal(name="new_goal", params={})
        agent_entity.add_goal(new_goal)
        assert len(agent_entity.goals) == 2

        # Get goal
        goal = agent_entity.get_goal("test_goal")
        assert goal is not None
        assert goal.name == "test_goal"

        # Remove goal
        removed = agent_entity.remove_goal("new_goal")
        assert removed
        assert len(agent_entity.goals) == 1

        # Remove non-existent goal
        removed = agent_entity.remove_goal("nonexistent")
        assert not removed

    async def test_perceive(self, agent_entity):
        """Test message perception."""
        message = Message.create(
            topic="test",
            payload={"observation": {"data": "test_obs"}},
            sender="test_sender"
        )

        initial_beliefs = len(agent_entity.state.beliefs)
        initial_memory = len(agent_entity.state.memory)

        await agent_entity.perceive(message)

        # Should have updated beliefs and memory
        assert len(agent_entity.state.beliefs) > initial_beliefs
        assert len(agent_entity.state.memory) > initial_memory

    async def test_act_once(self, agent_entity):
        """Test single action cycle."""
        initial_memory = len(agent_entity.state.memory)

        await agent_entity.act_once()

        # Should have updated memory with execution results
        assert len(agent_entity.state.memory) > initial_memory

    async def test_stop(self, agent_entity):
        """Test agent stopping."""
        agent_entity.running = True
        await agent_entity.stop()

        assert not agent_entity.running


class TestFactory:
    """Test factory functions."""

    def test_create_agent_entity(self):
        """Test agent entity creation via factory."""
        goals = [Goal(name="test", params={})]
        skills = {"test_skill": lambda s, c: s}
        goal_to_plan = {"test": sequence(Task("test_skill"))}

        agent = create_agent_entity(
            agent_id="factory_test",
            goals=goals,
            skills=skills,
            goal_to_plan=goal_to_plan
        )

        assert agent.aid == "factory_test"
        assert len(agent.goals) == 1
        assert "test_skill" in agent.skills

    def test_create_agent_with_persistence(self):
        """Test agent creation with persistence."""
        with tempfile.TemporaryDirectory() as temp_dir:
            persistence_path = Path(temp_dir) / "agent_state.json"

            goals = [Goal(name="test", params={})]
            skills = {"test_skill": lambda s, c: s}
            goal_to_plan = {"test": sequence(Task("test_skill"))}

            agent = create_agent_entity(
                agent_id="persistent_test",
                goals=goals,
                skills=skills,
                goal_to_plan=goal_to_plan,
                persistence_path=str(persistence_path)
            )

            # Test persistence
            agent.persist(agent.state)
            assert persistence_path.exists()

            # Verify JSON content
            with open(persistence_path) as f:
                data = json.load(f)
                assert "data" in data
                assert "memory" in data
                assert "beliefs" in data

    def test_create_simple_bus(self):
        """Test simple bus creation."""
        bus = create_simple_bus()
        assert isinstance(bus, SimpleBus)

    async def test_run_multi_agent_system(self):
        """Test multi-agent system execution."""
        # Create two agents
        goals1 = [Goal(name="goal1", params={})]
        goals2 = [Goal(name="goal2", params={})]
        skills = {"test_skill": lambda s, c: s}
        goal_to_plan = {"goal1": sequence(Task("test_skill")), "goal2": sequence(Task("test_skill"))}

        bus = MessageBus()

        agent1 = create_agent_entity(
            agent_id="agent1",
            goals=goals1,
            skills=skills,
            goal_to_plan=goal_to_plan,
            bus=bus
        )

        agent2 = create_agent_entity(
            agent_id="agent2",
            goals=goals2,
            skills=skills,
            goal_to_plan=goal_to_plan,
            bus=bus
        )

        # Run system for short duration
        await run_multi_agent_system([agent1, agent2], bus, duration=0.1)

        # Agents should have been stopped
        assert not agent1.running
        assert not agent2.running


class TestIntegration:
    """Integration tests for agent entities."""

    async def test_research_agent_entity(self):
        """Test a research agent as an entity."""
        # Define research skills
        async def search_skill(state: dict, ctx: dict) -> dict:
            return {**state, "search_results": ["result1", "result2"]}

        async def synthesize_skill(state: dict, ctx: dict) -> dict:
            results = state.get("search_results", [])
            return {**state, "synthesis": f"Synthesized from {len(results)} results"}

        skills = {
            "search": search_skill,
            "synthesize": synthesize_skill
        }

        # Define research plan
        research_plan = sequence(
            Task("search"),
            Task("synthesize")
        )

        # Create research goal
        research_goal = Goal(
            name="research_topic",
            params={"topic": "artificial intelligence", "depth": "comprehensive"}
        )

        # Create agent
        agent = create_agent_entity(
            agent_id="research_agent",
            goals=[research_goal],
            skills=skills,
            goal_to_plan={"research_topic": research_plan}
        )

        # Test single action cycle
        await agent.act_once()

        assert len(agent.state.memory) > 0
        execution_memory = list(agent.state.memory.values())[0]
        assert "result" in execution_memory
        from src.LambdaCat.agents.core.effect import Ok
        assert isinstance(execution_memory["result"], Ok)

    async def test_reactive_agent_entity(self):
        """Test a reactive agent that responds to events."""
        async def process_event_skill(state: dict, ctx: dict) -> dict:
            event = state.get("current_event", {})
            return {**state, "processed": True, "event_type": event.get("type", "unknown")}

        skills = {"process_event": process_event_skill}
        reactive_plan = sequence(Task("process_event"))
        reactive_goal = Goal(
            name="process_events",
            params={"priority": "high", "timeout": 5.0}
        )

        agent = create_agent_entity(
            agent_id="reactive_agent",
            goals=[reactive_goal],
            skills=skills,
            goal_to_plan={"process_events": reactive_plan}
        )

        event_message = Message.create(
            topic="events",
            payload={"observation": {"type": "alert", "severity": "high"}},
            sender="environment"
        )

        await agent.perceive(event_message)
        await agent.act_once()

        assert len(agent.state.memory) > 0

        execution_memory = None
        for key, value in agent.state.memory.items():
            if key.startswith("execution_"):
                execution_memory = value
                break

        assert execution_memory is not None
        from src.LambdaCat.agents.core.effect import Ok
        assert isinstance(execution_memory["result"], Ok)
        result_data = execution_memory["result"].value
        assert result_data.get("processed", False)
