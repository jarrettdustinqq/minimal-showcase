import unittest

from boundary_operator.agent import make_agent


class AgentSmokeTests(unittest.TestCase):
    def test_agent_constructs_without_model_credentials(self):
        agent = make_agent()
        self.assertIsNotNone(agent)


if __name__ == "__main__":
    unittest.main()
