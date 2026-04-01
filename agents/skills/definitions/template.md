# Skill Definition Template

## Metadata
- **Name**: [Skill Name]
- **Version**: [1.0.0]
- **Author**: [Author Name]
- **Description**: [Brief description of what the skill does]
- **Tags**: [tag1, tag2, domain]

## Input Specification
Define the input parameters required by this skill.

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `input_data` | `string/json/file` | Yes | The primary data to process |
| `options` | `dict` | No | Optional configuration parameters |

## Output Specification
Define the expected output format.

| Field | Type | Description |
| :--- | :--- | :--- |
| `result` | `any` | The processed result |
| `metadata` | `dict` | Execution metadata (time, confidence, etc.) |

## Usage Scenarios
- Scenario 1: [Description]
- Scenario 2: [Description]

## Dependencies
- library-name >= version

## Example
```json
{
  "input_data": "...",
  "options": { ... }
}
```
