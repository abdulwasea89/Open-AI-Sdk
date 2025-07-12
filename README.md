# OPEN SDK FULL COURSE

## Agents

### Basic Configuration:
The most common properties of an agent you'll configure are:
- Instructions: also known as a developer msg or system prompt.
- Model: which LLM to use and optional model_setting to configure model tuning parameters like temp, top_p
- Tools: Tools that the Agent can use to achive its tasks

## Agent Systax

    agent = Agent(
        name = params.name,
        instrucitons = params.instrucitons,
        tools = [
            tool.name,
            tool.name
        ]
    )
Here the `agent` is a var & `Agent` is a Class where is has many parameter you can use in your code

## Output Types

Agent Produce plain text (i.e. `str` ) outputs. if you want a structure output, you can use this technique for structure outputs. if you want the agent to produce particular type of output, you can use `output_type` parameter in `Agent` Class. A common choice is to use `pydantic` Objects, but you can use any type wrapped in Pydantic TypeAdapter (`BaseModel`).
    
    from pydantic import BaseModel
    from agents import Agent 

    class CalanderEvent(BaseModel):
        name: str
        date: str
        participants: list[str]

    agent = Agent(
        name = "Calender Extracter",
        instructions = "Extract calender events from text",
        output_type = CalenderEvent
    )

Here is the Code, How we can use the Output types in Agent, basically first we import the Pydantic TypeAdapter from pydantic, then we make a class with some parameters like name and some more. we initialize the agent with `Agent` Class and with the name Calender Extracter.

#### Senario:
Here is the Senario, You'll Consider:

    You have some text here & in the text you have name for the calender and data and people who attend the 
    event, so Agent Extract the data, but wait we want structured output so the agent will extract the 
    name and all the params the user wants & uses the class that we inserted in the output type to make
    the desire output for the user

### IF IT FAILS

So, if the agent is not getting the disire output and fails what do you think about that agent will stop or retry or exception , think about this ......
In my Oppinoin and ChatGPT, the execution stops


>Note : When you pass an `output_type`, that tells the model to use structured outputs instead of regural plain text responses (i.e. `str`)

## Hands Offs
Handoffs are subs-agents that the agent can delegate to. You provide a list of handoffs, and the agent can choose to delegate to them if relevent. This is a powerfull pattern that allows orchestrating modular, specializing agents that excel at a single tasks 

    from agents import Agent 
    
    booking_agent = Agent(...)
    refund_agent = Agent(...)

    triage_agent = Agent(
        name = "Triage agent",
        instructions = "...",
        handoffs = [
            booking_agent,
            refund_agent
        ]
    )

## Dynamic instructions 

In most cases, you can provide intructions when you create the agent. However, you can also provide dynamic instruction via a function. The function will recieve the agent and context, and must the prompt. Both regular and `async` functions are accepted.

    def dynamic_instructions(
    context: RunContextWrapper[UserContext], agent: Agent[UserContext]
    ) -> str:
    return f"The user's name is {context.context.name}. Help them with their questions."


    agent = Agent[UserContext](
    name="Triage agent",
    instructions=dynamic_instructions,
    )

## LifeCycle events (hooks)

Sometimes, you want to observe the lifecycle of an agent. For example, you may want to log event or pre-fetch data when certain events occur. You can hook into agent lifecycle with the `hooks` property. Subclass the `AgentHook` class and override the methods you're interested in.

## Guardrails

Guardrails allow you to run checks/validation on user input, in parallel to the agent running. For Example, you could screen the user's input for relevence. Read more on `guardrails` page on openai agent sdk.

## Cloning/Coping agents

By using the `clone()` method on the agent, you can duplicate agents & you can change any paramerter of the agent by cloning

    abc = Agent(
        name = "...",
        instructions = "..."
    )

    def = abc.clone(
        name = "...",
        instructions = "..."
    )

## Forcing tools use

Supplying a list of tools doesn't always mean the LLM will use a tool. You can force tool use by setting ModelSettings.tool_choice. Valid values are:

 - `auto`, which allows the LLM to decide whether or not to use a tool.
 - `required`, which requires the LLM to use a tool (but it can intelligently decide which tool).
 - `none`, which requires the LLM to not use a tool.
 - `Setting` a specific string e.g. `my_tool`, which requires the LLM to use that specific tool.

 > To prevent infinite loops, the framework automatically resets tool_choice to `"auto" `after a tool call. This behavior is configurable via agent.reset_tool_choice. The infinite loop is because tool results are sent to the LLM, which then generates another tool call because of tool_choice, ad infinitum. If you want the Agent to completely stop after a tool call (rather than continuing with auto mode), you can set `[Agent.tool_use_behavior="stop_on_first_tool"] `which will directly use the tool output as the final response without further LLM processing.