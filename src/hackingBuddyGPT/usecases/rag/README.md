# ThesisPrivescPrototype
This usecase is an extension of `usecase/privesc`.

## Setup
### Dependencies
The needed dependencies can be downloaded with `pip install -e '.[rag-usecase]'`. If you encounter the error `unexpected keyword argument 'proxies'` after trying to start the usecase, try downgrading `httpx` to 0.27.2.
### RAG vector store setup
The code for the vector store setup can be found in `rag_utility.py`. Currently the vector store uses two sources: `GTFObins` and `hacktricks`. To use RAG, download the markdown files and place them in `rag_storage/GTFObinMarkdownfiles` (`rag_storage/hacktricksMarkdownFiles`). You can download the markdown files either from the respective github repository ([GTFObin](https://github.com/GTFOBins/GTFOBins.github.io/tree/master), [hacktricks](https://github.com/HackTricks-wiki/hacktricks/tree/master/src/linux-hardening/privilege-escalation)) or scrape them from their website ([GTFObin](https://gtfobins.github.io/), [hacktricks](https://book.hacktricks.wiki/en/linux-hardening/privilege-escalation/index.html)).

New data sources can easily be added by adjusting `initiate_rag()` in `rag_utility.py`.

## Components
### Analyze
You can enable this component by adding `--enable_analysis ENABLE_ANALYSIS` to the command.

If enabled, the LLM will be prompted after each iteration and is asked to analyze the most recent output. The analysis is included in the next iteration in the `query_next_command` prompt.
### Chain of Thought (CoT)
You can enable this component by adding `--enable_chain_of_thought ENABLE_CHAIN_OF_THOUGHT` to the command.

If enabled, CoT is used to generate the next command. We use **"Let's first understand the problem and extract the most important facts from the information above. Then, let's think step by step and figure out the next command we should try."**
### Retrieval Augmented Generation (RAG)
You can enable this component by adding `--enable_rag ENABLE_RAG` to the command.

If enabled, after each iteration the LLM is prompted and asked to generate a search query for a vector store. The search query is then used to retrieve relevant documents from the vector store and the information is included in the prompt for the Analyze component (Only works if Analyze is enabled).
### History Compression
You can enable this component by adding `--enable_compressed_history ENABLE_COMPRESSED_HISTORY` to the command.

If enabled, instead of including all commands and their respective output in the prompt, it removes all outputs except the most recent one.
### Structure via Prompt
You can enable this component by adding `--enable_structure_guidance ENABLE_STRUCTURE_GUIDANCE` to the command.

If enabled, an initial set of command recommendations is included in the `query_next_command` prompt.
