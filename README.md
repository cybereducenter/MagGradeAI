# MagGradeAI - Automated C Code Grader

MagGradeAI is a LangGraph-based pipeline that prepares grading prompts and generates feedback for C programming exercises.

## Getting Started

This guide covers local setup and the streamlined preprocessing + feedback flow.

### Local Setup

#### Prerequisites

- Python 3.10+
- Pip for package management
- `gcc` for compiling C code

#### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    ```

2.  **Set up the environment:**
    - Create a virtual environment:
      ```bash
      python -m venv .venv
      source .venv/bin/activate
      ```
    - Install the required dependencies:
      ```bash
      make install
      ```

3.  **Configure API Keys:**
    - Copy the example environment file:
      ```bash
      cp .env.example .env
      ```
    - Set the required keys in `.env`:
      ```
      OPENAI_API_KEY=your-key
      LANGCHAIN_API_KEY=your-langsmith-key
      # optionally:
      LANGCHAIN_PROJECT=MagGradeAI-Feedback
      ```

### Cloud Setup (EC2 Ubuntu)

#### 1. Set Up an EC2 Instance

1.  **Launch an EC2 Instance**:
    *   Choose an **Ubuntu** Amazon Machine Image (AMI).
    *   Select an instance type (e.g., `t2.micro` or `t3.small`).
    *   Configure a security group to allow SSH access (port 22).
    *   Launch the instance and save your private key file (`.pem`).

2.  **Connect to your instance**:
    ```bash
    ssh -i /path/to/your-key.pem ubuntu@<your-ec2-instance-public-ip>
    ```

#### 2. Install Prerequisites

Once connected to your EC2 instance, install Python, pip, git, and gcc.
```bash
sudo apt-get update
sudo apt-get install -y python3.10 python3.10-venv python3-pip git gcc
```

#### 3. Set Up the Project

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd MagGradeAI
    ```

2.  **Create a virtual environment**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    make install
    ```

4.  **Configure API Keys**:
    ```bash
    cp .env.example .env
    nano .env
    ```
    Add your API key to the `.env` file.

### Usage

To generate feedback:

1. Ensure your rubric is defined at `rubrics/rubric.yaml` (see below for format).
2. Provide preprocessing input JSON (default `examples/preprocessing_input.json`) that lists the references and debug exercises.
3. Place student `.c` files in a directory (default `sample_submission/ex08`).
4. Run:
   ```bash
   python3 main.py \
     --preprocess-input examples/preprocessing_input.json \
     --submission-dir sample_submission/ex08 \
     --output feedback_output.json
   ```
5. The output `feedback_output.json` contains per-exercise aggregated feedback. LangSmith traces are emitted when `LANGCHAIN_TRACING_V2=true`.

## Preprocessing Graph

Builds checker prompts per exercise:

- Usage:
  ```bash
  python3 scripts/run_preprocessing_graph.py --output preprocessing_output.json
  ```
- Input: `examples/preprocessing_input.json` (rubric path, reference solutions, debug exercises).
- Output: `prompts_by_exercise` mapping with 4 prompts per regular exercise and 1 prompt per debug exercise that lists required fixes. The script omits intermediate fields from the saved JSON.

## Developer Guide: Micro-Agent Architecture

The feedback system (`src/graphs/feedback.py`) uses a modular Micro-Agent architecture tailored to the exercise rubric.

### 1. Architecture Components

- **Orchestrator (`feedback.py`)**: The central LangGraph workflow. It does NOT run all agents blindly. Instead, it uses **Conditional Edges** to route execution.
- **Micro-Agents**: Specialized agents (e.g., `FlowStructureAgent`, `ProgrammingErrorsAgent`) that inherit from `BaseAgent`. They output strict JSON.
- **State (`FeedbackState`)**: Holds the code, description, and crucially, the `rubric_config` for the specific exercise.
- **Aggregator**: Collects all agent outputs into a final unified report.

### 2. The Conditional Edge Process (Dynamic Routing)

The core innovation is the dynamic routing at the start of the graph:

1.  **Input Configuration**: When the graph starts, it receives a `rubric_config` object (loaded from `rubrics/rubric.yaml`).
2.  **`route_to_agents` Function**:
    - This function inspects `rubric_config['type']`.
    - **Debug Exercises**: Routes only to `DebugTasksAgent`.
    - **Regular Exercises**: Iterates through `rubric_config['subtopics']` and routes **only** to the corresponding agents (e.g., if "Flow" is listed, `FlowStructureAgent` is activated).
3.  **Parallel Execution**: The selected agents run in parallel.
4.  **Aggregation**: All results are gathered by the `aggregator` node.

**Code Reference:**
```python
# src/graphs/feedback.py

def route_to_agents(state: FeedbackState):
    config = state.get("rubric_config", {})
    # ... logic to select next_nodes based on config ...
    return next_nodes

workflow.add_conditional_edges(START, route_to_agents, destinations)
```

### 3. Adding a New Agent

1. Creates a new class in `src/graphs/feedback_agents/agents/` inheriting from `BaseAgent`.
2. Define its `role_description` and `get_system_prompt`.
3. Register it in `src/graphs/feedback.py`:
    - Add to `agents` list.
    - Add mapping logic in `route_to_agents`.

## Rubric Format

`rubrics/rubric.yaml` lists exercises. Regular exercises have four subtopics; debug exercises list required fixes:

```yaml
exercises:
  - id: Exc2
    type: regular
    subtopics:
      - id: flow_structure
        topic: "Flow and Structure"
        text: "The series sum can be computed via a loop or via the geometric-series formula."
      # ...three more subtopics...
  - id: Exc4_cyberKioskSolution
    type: debug
    fixes:
      - "In takeOrder, add the missing ampersand (&) in the scanf that reads hasTlush."
      # ...more fixes...
```

## Running on EC2 (optional)

- SSH: `ssh -i /path/to/key.pem ubuntu@35.164.240.64`
- Activate venv: `source /home/ubuntu/MagGradeAI/MagGradeAIEnv/bin/activate`
- Run the same commands as in local usage.
