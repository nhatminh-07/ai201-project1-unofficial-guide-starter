# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

Domain: publicly documented traditional ecological knowledge about climate resilience, forest protection, and relationships with useful plants and trees.

This knowledge is valuable because it records practical, place-based ways that communities understand local ecosystems: how people identify useful plants, protect forests, manage seasonal changes, and maintain relationships with land, water, and trees. It is hard to replace because much of it is embodied through lived experience, oral tradition, and long-term observation rather than formal environmental reports. An unofficial guide in this domain could help users find community-centered environmental knowledge that supports climate adaptation and conservation, while avoiding private, sacred, or culturally restricted knowledge.

<!-- What domain did you choose? Why is this knowledge valuable and hard to find through official channels? -->

---

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | IPBES (Intergovernmental Science-Policy Platform on Biodiversity and Ecosystem Services) | Global assessments and guidance on indigenous and local knowledge relevant to biodiversity and resilience. | https://ipbes.net/
| 2 | "Weathering Uncertainty: Traditional Knowledge for Climate Change Assessment and Adaptation" (UNESCO / UNU report) | Compilation of case studies and methods linking traditional knowledge and climate adaptation. | https://unesdoc.unesco.org/ (search title)
| 3 | FAO — Indigenous Peoples portal | FAO resources on indigenous peoples' roles in sustainable forestry, agroecology, and resilience. | https://www.fao.org/indigenous-peoples/en/
| 4 | UNFCCC — Local Communities and Indigenous Peoples Platform | UNFCCC platform for knowledge exchange on local and indigenous practices for climate action. | https://unfccc.int/topics/local-communities-and-indigenous-peoples-platform
| 5 | UN — Declaration on the Rights of Indigenous Peoples (background/resources) | Legal and policy context for working with indigenous knowledge and rights. | https://www.un.org/development/desa/indigenouspeoples/declaration-on-the-rights-of-indigenous-peoples.html
| 6 | eHRAF World Cultures (Yale) | Ethnographic collections searchable for documented traditional ecological knowledge and plant use. | https://ehrafworldcultures.yale.edu/
| 7 | JSTOR Plants | Aggregated plant specimen images and literature references useful for linking local plant names to scientific taxa. | https://plants.jstor.org/
| 8 | PROTA (Plant Resources of Tropical Africa) / PROTA4U | Community and scientific database documenting uses, distribution, and vernacular names of African useful plants. | https://www.prota4u.org/
| 9 | Ethnobotany Research & Applications (open-access journal) | Peer-reviewed articles documenting local plant knowledge, uses, and conservation. | https://ethnobotanyjournal.org/
| 10 | The Christensen Fund — Biocultural resources | NGO resources and case studies on biocultural diversity, seed sovereignty, and community knowledge. | https://www.christensenfund.org/

---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:**  
Around 150-250 tokens, or roughly 120-200 words.

**Overlap:**  
Around 30-50 tokens, or roughly 20-40 words.

**Reasoning:**  
The sources are likely to contain reports, case studies, policy pages, and ethnobotanical descriptions where important ideas are usually grouped by paragraph. A 150-250 token chunk is large enough to preserve one complete idea, such as a plant use, climate adaptation practice, forest-management method, or community example, without mixing too many unrelated topics. A 30-50 token overlap helps prevent key context from being lost when a paragraph boundary splits related information, such as the community name, plant name, location, and practice description.

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:**
I would use [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2). It is a small models

**Top-k:**
I will retrieve the top 5 chunks for each query. Five chunks should give the generator enough evidence from multiple sources without adding too much unrelated context. If the answers are too broad or include irrelevant evidence, I will reduce top-k to 3; if answers are missing important context, I will test top-k values of 6-8.

**Production tradeoff reflection:**
If this were deployed for real users and I were allowed to choose the embedding model, I would compare models based on accuracy for traditional ecological knowledge, multilingual support, context length, latency, and whether the model can run locally. Multilingual support would matter because source documents may include place names, community names, and plant names from many languages. Higher accuracy and longer context could improve retrieval for domain-specific passages, but may increase cost and response time. For this project, since the embedding model is fixed, I will evaluate retrieval quality through test questions and adjust chunking or top-k instead of changing models.

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1.

2.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:**

**Milestone 4 — Embedding and retrieval:**

**Milestone 5 — Generation and interface:**
