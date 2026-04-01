from core.skill import Skill

class TestSkillSync(Skill):
    def __init__(self):
        super().__init__(
            name="test-skill-sync",
            description="Test sync",
            input_schema={},
            output_schema={}
        )

    def execute(self, inputs, **kwargs):
        # Implement your skill logic here
        return {"status": "success", "message": "Hello from test-skill-sync"}
