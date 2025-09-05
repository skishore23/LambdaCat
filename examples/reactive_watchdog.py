#!/usr/bin/env python3
"""
Reactive Watchdog Agent Demo

This example demonstrates a reactive agent that continuously monitors
an environment and responds to events using the async agent system.
"""

import asyncio
import json
import random
import time
from pathlib import Path
from typing import Dict, Any, List

# Import the async agent system
from LambdaCat.agents.core.compile_async import run_plan
from LambdaCat.agents.core.effect import Effect, with_trace
from LambdaCat.agents.core.bus import create_bus, create_agent_communicator
from LambdaCat.agents.core.instruments import get_observability, span, timer
from LambdaCat.agents.core.persistence import create_backend, PersistenceManager
from LambdaCat.agents.cognition.memory import AgentState
from LambdaCat.agents.cognition.beliefs import BeliefSystem, create_belief_system
from LambdaCat.agents.cognition.policy import BeliefBasedPolicy, create_belief_based_policy
from LambdaCat.agents.tools.llm import create_mock_llm
from LambdaCat.agents.tools.http import create_http_adapter
from LambdaCat.agents.tools.search import create_mock_search_adapter
from LambdaCat.agents.actions import task, sequence, parallel, choose


class Environment:
    """Simulated environment that generates events."""
    
    def __init__(self):
        self.events = []
        self.running = False
        self.metrics = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "disk_usage": 0.0,
            "network_latency": 0.0,
            "error_rate": 0.0
        }
    
    async def start(self):
        """Start the environment simulation."""
        self.running = True
        asyncio.create_task(self._simulate_metrics())
        asyncio.create_task(self._generate_events())
    
    async def stop(self):
        """Stop the environment simulation."""
        self.running = False
    
    async def _simulate_metrics(self):
        """Simulate system metrics."""
        while self.running:
            # Simulate realistic metric changes
            self.metrics["cpu_usage"] = max(0, min(100, self.metrics["cpu_usage"] + random.uniform(-5, 5)))
            self.metrics["memory_usage"] = max(0, min(100, self.metrics["memory_usage"] + random.uniform(-2, 2)))
            self.metrics["disk_usage"] = max(0, min(100, self.metrics["disk_usage"] + random.uniform(-1, 1)))
            self.metrics["network_latency"] = max(0, self.metrics["network_latency"] + random.uniform(-10, 10))
            self.metrics["error_rate"] = max(0, min(1, self.metrics["error_rate"] + random.uniform(-0.01, 0.01)))
            
            await asyncio.sleep(1.0)  # Update every second
    
    async def _generate_events(self):
        """Generate random events."""
        event_types = [
            "high_cpu", "high_memory", "high_disk", "high_latency", "high_errors",
            "low_cpu", "low_memory", "low_disk", "low_latency", "low_errors",
            "system_restart", "service_down", "service_up", "security_alert"
        ]
        
        while self.running:
            # Generate events based on metrics
            if self.metrics["cpu_usage"] > 80:
                await self._emit_event("high_cpu", {"cpu_usage": self.metrics["cpu_usage"]})
            elif self.metrics["cpu_usage"] < 20:
                await self._emit_event("low_cpu", {"cpu_usage": self.metrics["cpu_usage"]})
            
            if self.metrics["memory_usage"] > 85:
                await self._emit_event("high_memory", {"memory_usage": self.metrics["memory_usage"]})
            elif self.metrics["memory_usage"] < 30:
                await self._emit_event("low_memory", {"memory_usage": self.metrics["memory_usage"]})
            
            if self.metrics["error_rate"] > 0.1:
                await self._emit_event("high_errors", {"error_rate": self.metrics["error_rate"]})
            
            # Random events
            if random.random() < 0.1:  # 10% chance per second
                event_type = random.choice(event_types)
                await self._emit_event(event_type, {"random": True})
            
            await asyncio.sleep(1.0)
    
    async def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit an event."""
        event = {
            "type": event_type,
            "timestamp": time.time(),
            "data": data,
            "id": f"event_{len(self.events)}"
        }
        self.events.append(event)
        print(f"🔔 Event: {event_type} - {data}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return dict(self.metrics)
    
    def get_recent_events(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent events."""
        return self.events[-count:]


class WatchdogAgent:
    """Reactive watchdog agent that monitors and responds to events."""
    
    def __init__(self, agent_id: str, bus, persistence: PersistenceManager):
        self.agent_id = agent_id
        self.bus = bus
        self.persistence = persistence
        self.communicator = None
        self.belief_system = create_belief_system()
        self.policy = None
        self.obs = get_observability()
        self.running = False
        
        # Initialize beliefs
        self._initialize_beliefs()
    
    def _initialize_beliefs(self):
        """Initialize agent beliefs."""
        # System health beliefs
        self.belief_system = self.belief_system.add_belief(
            "system_healthy", 0.0, 0.8, "initialization"
        )
        self.belief_system = self.belief_system.add_belief(
            "needs_attention", -2.0, 0.6, "initialization"
        )
        self.belief_system = self.belief_system.add_belief(
            "critical_issue", -5.0, 0.3, "initialization"
        )
        
        # Action effectiveness beliefs
        self.belief_system = self.belief_system.add_belief(
            "restart_effective", 1.0, 0.7, "initialization"
        )
        self.belief_system = self.belief_system.add_belief(
            "alert_effective", 0.5, 0.8, "initialization"
        )
        self.belief_system = self.belief_system.add_belief(
            "monitor_effective", 1.5, 0.9, "initialization"
        )
        
        # Create policy
        utility_functions = {
            "system_health": self._compute_system_health_utility,
            "stability": self._compute_stability_utility,
            "responsiveness": self._compute_responsiveness_utility
        }
        self.policy = create_belief_based_policy(self.belief_system, utility_functions)
    
    def _compute_system_health_utility(self, state: Dict[str, Any]) -> float:
        """Compute utility based on system health."""
        metrics = state.get("metrics", {})
        cpu = metrics.get("cpu_usage", 50)
        memory = metrics.get("memory_usage", 50)
        errors = metrics.get("error_rate", 0)
        
        # Health score (0-1, higher is better)
        cpu_score = 1.0 - abs(cpu - 50) / 50  # Optimal around 50%
        memory_score = 1.0 - abs(memory - 50) / 50
        error_score = 1.0 - min(errors * 10, 1.0)  # Penalize high error rates
        
        return (cpu_score + memory_score + error_score) / 3
    
    def _compute_stability_utility(self, state: Dict[str, Any]) -> float:
        """Compute utility based on system stability."""
        events = state.get("recent_events", [])
        if not events:
            return 1.0  # No events = stable
        
        # Count critical events
        critical_events = [e for e in events if e.get("type") in ["high_cpu", "high_memory", "high_errors", "security_alert"]]
        stability_score = 1.0 - min(len(critical_events) / 10, 1.0)
        
        return stability_score
    
    def _compute_responsiveness_utility(self, state: Dict[str, Any]) -> float:
        """Compute utility based on system responsiveness."""
        metrics = state.get("metrics", {})
        latency = metrics.get("network_latency", 0)
        
        # Responsiveness score (0-1, higher is better)
        if latency < 50:
            return 1.0
        elif latency < 100:
            return 0.8
        elif latency < 200:
            return 0.6
        else:
            return 0.2
    
    async def start(self):
        """Start the watchdog agent."""
        self.communicator = await create_agent_communicator(self.agent_id, self.bus)
        self.running = True
        
        # Start reactive loop
        asyncio.create_task(self._reactive_loop())
    
    async def stop(self):
        """Stop the watchdog agent."""
        self.running = False
    
    async def _reactive_loop(self):
        """Main reactive loop."""
        inbox = await self.communicator.get_inbox()
        
        while self.running:
            try:
                # Check for messages with timeout
                try:
                    message = await asyncio.wait_for(inbox.get(), timeout=1.0)
                    await self._handle_message(message)
                except asyncio.TimeoutError:
                    # No message, continue monitoring
                    pass
                
                # Periodic monitoring
                await self._monitor_system()
                
            except Exception as e:
                print(f"❌ Watchdog error: {e}")
                await asyncio.sleep(1.0)
    
    async def _handle_message(self, message):
        """Handle incoming messages."""
        if message.topic == "environment_update":
            # Update beliefs based on environment data
            env_data = message.payload
            await self._update_beliefs_from_environment(env_data)
        
        elif message.topic == "action_feedback":
            # Update beliefs based on action results
            feedback = message.payload
            await self._update_beliefs_from_feedback(feedback)
    
    async def _monitor_system(self):
        """Monitor system and take actions."""
        # Get current state
        state = await self._get_current_state()
        
        # Evaluate available actions
        actions = ["monitor", "alert", "restart_service", "scale_up", "investigate"]
        
        if self.policy:
            try:
                selected_action = self.policy.select_action(state, actions, {})
                await self._execute_action(selected_action, state)
            except Exception as e:
                print(f"❌ Policy error: {e}")
    
    async def _get_current_state(self) -> Dict[str, Any]:
        """Get current system state."""
        # Load from persistence
        agent_state = await self.persistence.load_agent_state(self.agent_id)
        if not agent_state:
            agent_state = AgentState()
        
        # Get environment data (in real system, this would come from monitoring)
        # For demo, we'll use simulated data
        state = {
            "metrics": {
                "cpu_usage": random.uniform(20, 90),
                "memory_usage": random.uniform(30, 85),
                "disk_usage": random.uniform(40, 80),
                "network_latency": random.uniform(10, 200),
                "error_rate": random.uniform(0, 0.2)
            },
            "recent_events": [
                {"type": "high_cpu", "timestamp": time.time() - 10},
                {"type": "low_memory", "timestamp": time.time() - 5}
            ],
            "agent_state": agent_state.to_dict(),
            "beliefs": self.belief_system.to_dict()
        }
        
        return state
    
    async def _update_beliefs_from_environment(self, env_data: Dict[str, Any]):
        """Update beliefs based on environment data."""
        metrics = env_data.get("metrics", {})
        events = env_data.get("events", [])
        
        # Update system health belief
        cpu = metrics.get("cpu_usage", 50)
        memory = metrics.get("memory_usage", 50)
        errors = metrics.get("error_rate", 0)
        
        if cpu > 80 or memory > 85 or errors > 0.1:
            # System needs attention
            self.belief_system = self.belief_system.update_belief(
                "needs_attention", 1.0, "environment_monitoring"
            )
            self.belief_system = self.belief_system.update_belief(
                "system_healthy", -1.0, "environment_monitoring"
            )
        else:
            # System is healthy
            self.belief_system = self.belief_system.update_belief(
                "system_healthy", 0.5, "environment_monitoring"
            )
            self.belief_system = self.belief_system.update_belief(
                "needs_attention", -0.5, "environment_monitoring"
            )
        
        # Check for critical events
        critical_events = [e for e in events if e.get("type") in ["high_cpu", "high_memory", "high_errors", "security_alert"]]
        if critical_events:
            self.belief_system = self.belief_system.update_belief(
                "critical_issue", 2.0, "critical_events"
            )
    
    async def _update_beliefs_from_feedback(self, feedback: Dict[str, Any]):
        """Update beliefs based on action feedback."""
        action = feedback.get("action")
        success = feedback.get("success", False)
        effectiveness = feedback.get("effectiveness", 0.5)
        
        if success:
            # Action was successful, increase belief in effectiveness
            belief_key = f"{action}_effective"
            self.belief_system = self.belief_system.update_belief(
                belief_key, effectiveness, "action_feedback"
            )
        else:
            # Action failed, decrease belief in effectiveness
            belief_key = f"{action}_effective"
            self.belief_system = self.belief_system.update_belief(
                belief_key, -effectiveness, "action_feedback"
            )
    
    async def _execute_action(self, action: str, state: Dict[str, Any]):
        """Execute the selected action."""
        print(f"🤖 {self.agent_id} executing action: {action}")
        
        if action == "monitor":
            await self._action_monitor(state)
        elif action == "alert":
            await self._action_alert(state)
        elif action == "restart_service":
            await self._action_restart_service(state)
        elif action == "scale_up":
            await self._action_scale_up(state)
        elif action == "investigate":
            await self._action_investigate(state)
    
    async def _action_monitor(self, state: Dict[str, Any]):
        """Monitor action - just observe and log."""
        metrics = state.get("metrics", {})
        print(f"📊 Monitoring: CPU={metrics.get('cpu_usage', 0):.1f}%, Memory={metrics.get('memory_usage', 0):.1f}%")
        
        # Update belief that monitoring is effective
        self.belief_system = self.belief_system.update_belief(
            "monitor_effective", 0.1, "action_execution"
        )
    
    async def _action_alert(self, state: Dict[str, Any]):
        """Alert action - send alert about issues."""
        print("🚨 Sending alert about system issues")
        
        # Simulate alert sending
        await asyncio.sleep(0.1)
        
        # Update belief
        self.belief_system = self.belief_system.update_belief(
            "alert_effective", 0.2, "action_execution"
        )
    
    async def _action_restart_service(self, state: Dict[str, Any]):
        """Restart service action."""
        print("🔄 Restarting service")
        
        # Simulate service restart
        await asyncio.sleep(0.5)
        
        # Update belief
        self.belief_system = self.belief_system.update_belief(
            "restart_effective", 0.3, "action_execution"
        )
    
    async def _action_scale_up(self, state: Dict[str, Any]):
        """Scale up action."""
        print("📈 Scaling up resources")
        
        # Simulate scaling
        await asyncio.sleep(0.3)
        
        # Update belief
        self.belief_system = self.belief_system.update_belief(
            "scale_effective", 0.2, "action_execution"
        )
    
    async def _action_investigate(self, state: Dict[str, Any]):
        """Investigate action."""
        print("🔍 Investigating system issues")
        
        # Simulate investigation
        await asyncio.sleep(1.0)
        
        # Update belief
        self.belief_system = self.belief_system.update_belief(
            "investigate_effective", 0.1, "action_execution"
        )
    
    async def save_state(self):
        """Save agent state to persistence."""
        agent_state = AgentState(
            data={"beliefs": self.belief_system.to_dict()},
            memory={"last_update": time.time()}
        )
        await self.persistence.save_agent_state(self.agent_id, agent_state)


async def run_watchdog_demo():
    """Run the reactive watchdog demo."""
    print("🐕 Starting Reactive Watchdog Demo")
    print("=" * 50)
    
    # Create components
    bus = await create_bus("request_reply")
    await bus.start()
    
    persistence_backend = create_backend("json", base_path="watchdog_states")
    persistence = PersistenceManager(persistence_backend)
    
    # Create environment
    env = Environment()
    await env.start()
    
    # Create watchdog agents
    watchdog1 = WatchdogAgent("watchdog_1", bus, persistence)
    watchdog2 = WatchdogAgent("watchdog_2", bus, persistence)
    
    await watchdog1.start()
    await watchdog2.start()
    
    try:
        # Run for 30 seconds
        print("🔄 Running watchdog agents for 30 seconds...")
        await asyncio.sleep(30)
        
        # Save states
        await watchdog1.save_state()
        await watchdog2.save_state()
        
        print("\n📊 Final Belief States:")
        print(f"Watchdog 1 beliefs: {watchdog1.belief_system.to_dict()}")
        print(f"Watchdog 2 beliefs: {watchdog2.belief_system.to_dict()}")
        
    finally:
        # Cleanup
        await watchdog1.stop()
        await watchdog2.stop()
        await env.stop()
        await bus.stop()
    
    print("✅ Watchdog demo completed!")


if __name__ == "__main__":
    asyncio.run(run_watchdog_demo())
