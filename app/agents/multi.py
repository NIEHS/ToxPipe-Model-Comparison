def run_parallel(self=None, prompt="", user_id=""):
    outputs = self.agent_with_chat_history.invoke({"input": prompt},  config={"configurable": {"conversation_id": f"{user_id}", "user_id": f"{user_id}"}},)
    return([outputs["output"]])