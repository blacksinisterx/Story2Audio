import os
from ollama import chat as ollama_chat

class OllamaModel():
   """Local Ollama-based implementation."""
  
   def __init__(self, model_name="llama3.1"):
       """
       Initialize the OllamaModel with the given model name.
      
       Args:
           model_name (str): The name of the Ollama model to use.
       """
       self.model_name = model_name
       self.system_prompt = """
       You are a teacher assitant working to generate lecture contents.
       """


   def create_assistant(self, instructions):
       # In Ollama, assistants are typically managed at the prompt level.
       # You can define a custom system prompt here.
       self.system_prompt = f"{instructions}"


   def generate_response(self, prompt,assitant = None):
       messages = [
           {"role": "system", "content": self.system_prompt},
           {"role": "user", "content": prompt}
       ]


       response = ""
       for chunk in ollama_chat(model=self.model_name, messages=messages, stream=True):
           response += chunk['message']['content']
      
       return response

