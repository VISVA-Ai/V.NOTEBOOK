# Orchestrates the AI Engine (RAG, Research, Automation, Cognitive)
import json
import speech_recognition as sr
from core.llm import LLMHandler
from core.ingestion import IngestionHandler
from core.memory import Memory
from core.research.researcher import Researcher
from core.graph import KnowledgeGraph
from core.personas import Personas

# Cognitive Modules
from core.goals import GoalManager
from core.feedback import FeedbackMemory
from core.insights import InsightMemory

# V.ASSISTANT — Controlled Execution System
from core.actions import ActionQueue
from core.context_manager import ContextManager
from core.assistant_chat import AssistantChatParser
from core.email_intelligence import EmailIntelligence
from core.decision_engine import DecisionEngine
from core.executor import Executor

# Audio generation (Stub if missing in V.NOTEBOOK, assuming it exists or imported from core.audio)
try:
    from core.audio import generate_audio
except ImportError:
    def generate_audio(text): return None



class Engine:
    def __init__(self):
        self.llm = LLMHandler()
        self.memory = Memory()
        self.researcher = Researcher()
        self.graph = KnowledgeGraph()
        self.recognizer = sr.Recognizer()
        
        # Cognitive Layer
        self.goals = GoalManager()
        self.feedback = FeedbackMemory()
        self.insights = InsightMemory()

        # V.ASSISTANT — Controlled Execution System
        self.action_queue = ActionQueue()
        self.context_manager = ContextManager()
        self.email_intelligence = EmailIntelligence(self.llm)
        self.assistant_parser = AssistantChatParser(self.llm, self.context_manager)
        self.executor = Executor(self.action_queue)
        self.decision_engine = DecisionEngine(
            parser=self.assistant_parser,
            action_queue=self.action_queue,
            context_manager=self.context_manager,
            email_intelligence=self.email_intelligence,
            executor=self.executor,
        )

    def assistant_process(self, user_text: str, session_id: str = "default",
                          thread_context: str = None) -> dict:
        """Main entry point for V.ASSISTANT chat."""
        return self.decision_engine.process(user_text, session_id, thread_context)

    def get_assistant_dashboard(self) -> dict:
        """Get assistant dashboard stats."""
        stats = self.action_queue.get_stats()
        return {
            "emails_pending": 0,
            "actions_pending": stats.get("pending", 0),
            "actions_today": stats.get("today", 0),
            "recommendations_active": 0,
            "calendar_suggestions": 0,
            "goals_active": len(self.goals.get_goals(status="active")),
            "top_priority_email": None,
        }

    def transcribe(self, audio_file):
        """Transcribes audio file object to text using Google Web Speech API."""
        try:
            with sr.AudioFile(audio_file) as source:
                audio_data = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio_data)
                return text
        except Exception as e:
            err_msg = str(e) or repr(e) or "Unknown error"
            return f"Error transcribing audio: {err_msg}"
        
    def _infer_goals(self, user_query: str, ai_response: str, session_id: str):
        """Background task to infer goals from conversation."""
        try:
            # Check if we already have too many goals
            active_goals = self.goals.get_goals(status="active", session_id=session_id)
            if len(active_goals) >= 5:
                return

            prompt = f"""
            Analyze this interaction and extract a research goal or topic.
            
            User: {user_query}
            AI: {ai_response[:500]}
            
            If a clear goal or research topic exists (e.g., "Research Sensor Technology", "Learn about Oracle AI"), return it as JSON.
            If generic chitchat or greeting, return {{}}.
            
            Format: {{"title": "Short Title", "description": "Brief description"}}
            """
            
            response = self.llm.get_response(prompt, system_prompt="You are a goal extraction engine. Output JSON only.")
            
            try:
                start = response.find('{')
                end = response.rfind('}') + 1
                if start != -1 and end > 0:
                    data = json.loads(response[start:end])
                    if data.get("title"):
                        from models.goals import GoalCreate
                        goal_create = GoalCreate(
                            session_id=session_id or "default",
                            title=data["title"],
                            description=data.get("description", ""),
                            source="inferred"
                        )
                        self.goals.add_goal(goal_create)
                        print(f"[Engine] Goal inferred: {data['title']}")
            except Exception:
                pass
                
        except Exception as e:
            print(f"Goal inference failed: {e}")

    def ingest_file(self, file_obj, session_id: str = None, progress_callback=None):
        """Processes an uploaded file into memory."""
        text = IngestionHandler.load_pdf(file_obj)
        if not text: return "Failed to extract text."
            
        chunks = IngestionHandler.chunk_text(text)
        total_chunks = len(chunks)
        
        # Prepare documents
        documents = [{'text': chunk, 'metadata': {'source': file_obj.name, 'session_id': session_id}} for chunk in chunks]
        
        # Add to memory (handles embedding internally)
        self.memory.add_documents(documents)
        
        # Build graph
        self.graph.build_graph(documents)
        
        # Notify
        print(f"[Engine] Document ingested: {file_obj.name}, {total_chunks} chunks")
        
        if progress_callback: progress_callback(1.0)
        return f"Processed {total_chunks} chunks."
        
    def query(self, user_query, mode="Fast Mode", model=None, chat_history=None, session_id=None, intent="Explore", do_not_learn=False):
        """
        Main query pipeline following the Prompt Constitution.
        """
        
        # 1. Base Persona
        system_prompt = Personas.get_prompt(mode)
        
        # 2. Session Intent
        intent_context = f"User Intent: The user's primary psychological mode for this session is '{intent}'. Tailor your response style accordingly." 
        
        # 3. Active Goals
        goals_context = ""
        feedback_context = ""
        insights_context = ""
        
        if not do_not_learn:
            matched_goals = self.goals.match_context(user_query, session_id=session_id)
            if matched_goals:
                goals_list = "\n".join([f"- {g.title}: {g.description}" for g in matched_goals])
                goals_context = f"Active Goals Context:\n{goals_list}\n"
                
            # 4. Feedback Directives
            ctx_type = "research" if mode in ["Deep Research", "Grounded Mode"] else "general"
            directives = self.feedback.get_preference_directives(ctx_type)
            if directives:
                directives_list = "\n".join([f"- {k}: {v}" for k, v in directives.items()])
                feedback_context = f"User Preferences:\n{directives_list}\n"
                
            # 5. Insight Memory
            relevant_insights = self.insights.get_relevant_insights(user_query)
            if relevant_insights:
                insights_list = "\n".join([f"- {i}" for i in relevant_insights])
                insights_context = f"Relevant Insights:\n{insights_list}\n"
            
        # 6. Retrieved Context (RAG)
        retrieved_context = ""
        sources = []
        if mode == "Grounded Mode":
            # Step 1: Broad retrieval (Reduced to k=10 to prevent hitting Groq TPM limits)
            results = self.memory.retrieve(user_query, k=10, session_id=session_id)
            if not results:
                return json.dumps({
                    "summary": "No sufficient sources found. Please upload documents or adjust your query.",
                    "key_points": [],
                    "evidence": [],
                    "gaps": ["No archived documents match your query in Grounded Mode."]
                }), []
            else:
                # Bypass LLM Reranking to prevent Groq API 429 Rate Limits
                # FAISS already sorted by L2/Cosine similarity, so just take the top 5
                results = results[:5]
                    
                sources = sorted(list(set([res['metadata'].get('source', 'Unknown') for res in results])))
                context_block = "\n\n".join([f"[{i+1}] {res['text']} (Source: {res['metadata'].get('source', 'Unknown')})" for i, res in enumerate(results)])
                retrieved_context = f"=== UPLOADED DOCUMENTS / ARCHIVE CONTEXT ===\n{context_block}\n=================================\n"
        
        elif mode == "Deep Research":
            # Delegate to Researcher for web search
            # Researcher handles its own context retrieval
            # But we should pass the COGNITIVE CONTEXT (Goals, Feedback) to it?
            # For now, let's keep it simple: run researcher, get text, then refine?
            # Or just return researcher output directly.
            # The current Researcher implementation is self-contained.
            # We will use it directly.
            response, sources = self.researcher.research(user_query, model=model)
            # We should technically log this interactions to goals/feedback too?
            print(f"[Engine] Deep research complete: {user_query[:80]}")
            return response, sources

        # 7. Construct Final System Prompt
        # Only enforce JSON contract for modes with structured retrieval
        json_instruction = ""
        if mode == "Grounded Mode":
            json_instruction = """
You MUST synthesize your final answer into a strict JSON object. Do not include markdown formatting like ```json.
The UPLOADED DOCUMENTS / ARCHIVE CONTEXT contains excerpts from the user's uploaded files (PDFs, notes, documents). If the user asks about "the PDF", "the document", or "my files", answer using THIS provided context!

Your response must follow this exact schema:
{
  "summary": "A concise paragraph addressing the prompt based on the documents.",
  "key_points": ["Key detail 1", "Key detail 2"],
  "evidence": [
    {"source": "filename.pdf", "text": "Exact quote from context validating the claim"}
  ],
  "gaps": ["Detail any missing information, uncertainty, or contradictions between sources"]
}
"""
        
        # Combine all layers
        final_system_prompt = (
            f"{system_prompt}\n\n"
            f"{intent_context}\n"
            f"{goals_context}\n"
            f"{feedback_context}\n"
            f"{insights_context}\n"
            f"{retrieved_context}\n"
            f"{json_instruction}"
        )
        
        # Execute LLM Call
        # We pass the constructed system prompt.
        # Note: LLMHandler usually takes `system_prompt` and `prompt`.
        # We will pass the `final_system_prompt` as the system instruction.
        
        response = self.llm.get_response(user_query, model=model, system_prompt=final_system_prompt, chat_history=chat_history)
        
        # 8. Post-Processing — Infer Goals
        if not do_not_learn:
            try:
                self._infer_goals(user_query, response, session_id=session_id)
            except Exception as e:
                print(f"[Engine] Goal inference error (non-fatal): {e}")
        
        print(f"[Engine] Query answered: {user_query[:80]}")
        
        return response, sources

    def generate_flashcards(self, session_id: str):
        """Generates flashcards based on recent conversation or uploaded documents."""
        # 1. Gather Context
        # Try to retrieve from memory first (documents)
        results = self.memory.retrieve("summary", k=5, session_id=session_id)
        context = ""
        if results:
            context = "\n".join([r['text'] for r in results])
        else:
            # Fallback to chat history?
            # context = ...
            pass

        if not context:
            return {"cards": [{"front": "No content found", "back": "Please upload a document or start a conversation first."}]}

        # 2. Prompt LLM
        prompt = (
            f"Generate 5 high-quality flashcards based on the following content. "
            f"Format as JSON: [{{'front': 'Question?', 'back': 'Answer', 'sources': 'Source name', 'type': 'definition | concept | contradiction', 'difficulty': 'easy | medium | hard'}}].\n\n"
            f"Content:\n{context[:4000]}"
        )
        
        response = self.llm.get_response(prompt, mode="Fast Mode", system_prompt="You are a study aid generator. Output ONLY valid JSON containing an array of flashcard objects.")
        
        # 3. Parse JSON
        try:
            start = response.find('[')
            end = response.rfind(']') + 1
            if start != -1 and end != -1:
                cards = json.loads(response[start:end])
                return {"cards": cards}
        except Exception as e:
            print(f"Flashcard generation error: {e}")
        
        return {"cards": [{"front": "Error generating", "back": "Please try again."}]}


    def generate_quiz(self, session_id: str):
        """Generates an interactive multiple-choice quiz based on uploaded documents."""
        results = self.memory.retrieve("summary key concepts definitions", k=10, session_id=session_id)
        context = ""
        if results:
            context = "\n".join([r['text'] for r in results])
        
        if not context:
            return {"questions": [{"question": "No content found", "options": ["Upload a document first"], "correct": 0, "explanation": "Please upload a document to generate a quiz."}]}

        prompt = (
            f"Generate 5 challenging multiple-choice quiz questions based on the following content. "
            f"Each question should test understanding, not just recall. "
            f"Format as JSON array: ["
            f'{{"question": "Question text?", "options": ["Option A", "Option B", "Option C", "Option D"], "correct": 0, "explanation": "Why this answer is correct.", "difficulty": "easy|medium|hard"}}]. '
            f"The 'correct' field is the 0-based index of the correct option.\n\n"
            f"Content:\n{context[:5000]}"
        )
        
        response = self.llm.get_response(
            prompt, 
            mode="Fast Mode", 
            system_prompt="You are an expert quiz generator. Output ONLY valid JSON containing an array of quiz question objects. No markdown formatting."
        )
        
        try:
            start = response.find('[')
            end = response.rfind(']') + 1
            if start != -1 and end != -1:
                questions = json.loads(response[start:end])
                return {"questions": questions}
        except Exception as e:
            print(f"Quiz generation error: {e}")
        
        return {"questions": [{"question": "Error generating quiz", "options": ["Please try again"], "correct": 0, "explanation": "Quiz generation failed.", "difficulty": "easy"}]}

    def generate_brief(self, session_id: str):
        """Generates an executive brief/summary from uploaded documents."""
        results = self.memory.retrieve("summary overview key findings", k=15, session_id=session_id)
        context = ""
        if results:
            context = "\n".join([r['text'] for r in results])
        
        if not context:
            return {"title": "No Content", "summary": "Please upload a document to generate a brief.", "key_findings": [], "entities": [], "open_questions": []}

        prompt = (
            "Generate a comprehensive executive brief based on the following source content. "
            "Return ONLY a JSON object (no markdown, no code fences) with this exact structure:\n"
            '{"title": "Brief Title", "summary": "A 2-3 paragraph executive summary.", '
            '"key_findings": ["Finding 1", "Finding 2", "Finding 3", "Finding 4", "Finding 5"], '
            '"entities": ["Entity/Concept 1", "Entity/Concept 2", "Entity/Concept 3"], '
            '"open_questions": ["Unanswered question 1", "Unanswered question 2"]}\n\n'
            f"Content:\n{context[:6000]}"
        )
        
        response = self.llm.get_response(
            prompt, 
            mode="Fast Mode", 
            system_prompt="You are an expert research analyst. Output ONLY valid JSON. No markdown. No code fences. No explanation. Just the JSON object."
        )
        
        try:
            # Strip markdown code fences if present
            cleaned = response.strip()
            cleaned = cleaned.replace('```json', '').replace('```', '').strip()
            
            start = cleaned.find('{')
            end = cleaned.rfind('}') + 1
            if start != -1 and end > start:
                brief = json.loads(cleaned[start:end])
                # Ensure all required fields exist
                brief.setdefault('title', 'Executive Brief')
                brief.setdefault('summary', '')
                brief.setdefault('key_findings', [])
                brief.setdefault('entities', [])
                brief.setdefault('open_questions', [])
                return brief
        except Exception as e:
            print(f"Brief generation error: {e}")
            print(f"Raw LLM response: {response[:500]}")
        
        # Last resort: return the raw text as the summary
        return {
            "title": "Document Brief", 
            "summary": response[:2000] if response else "Failed to generate brief. Please try again.", 
            "key_findings": [], 
            "entities": [], 
            "open_questions": []
        }

    def get_topics(self, session_id: str = None):
        """Extracts key topics from uploaded documents for quiz topic selection."""
        results = self.memory.retrieve("topics themes subjects categories", k=10, session_id=session_id)
        context = ""
        if results:
            context = "\n".join([r['text'] for r in results])
        
        if not context:
            return {"topics": []}

        prompt = (
            "Based on the following content, identify 5-8 distinct topics or themes covered. "
            "Return ONLY a JSON array of topic strings. No markdown, no code fences.\n"
            'Example: ["Sensor Technology", "Data Analysis", "Machine Learning"]\n\n'
            f"Content:\n{context[:4000]}"
        )
        
        response = self.llm.get_response(
            prompt, 
            mode="Fast Mode", 
            system_prompt="You are a topic extraction AI. Output ONLY a valid JSON array of strings. No markdown. No code fences."
        )
        
        try:
            cleaned = response.strip().replace('```json', '').replace('```', '').strip()
            start = cleaned.find('[')
            end = cleaned.rfind(']') + 1
            if start != -1 and end > start:
                topics = json.loads(cleaned[start:end])
                return {"topics": topics}
        except Exception as e:
            print(f"Topic extraction error: {e}")
        
        return {"topics": []}

    def generate_quiz_with_options(self, session_id: str, topic: str = "all", num_questions: int = 5):
        """Generates a quiz filtered by topic with configurable question count."""
        query = f"key concepts definitions about {topic}" if topic != "all" else "summary key concepts definitions"
        results = self.memory.retrieve(query, k=10, session_id=session_id)
        context = ""
        if results:
            context = "\n".join([r['text'] for r in results])
        
        if not context:
            return {"questions": [{"question": "No content found", "options": ["Upload a document first"], "correct": 0, "explanation": "Please upload a document to generate a quiz."}]}

        topic_instruction = f"Focus specifically on the topic: '{topic}'. " if topic != "all" else "Cover a variety of topics from the content. "

        prompt = (
            f"Generate exactly {num_questions} challenging multiple-choice quiz questions based on the following content. "
            f"{topic_instruction}"
            f"Each question should test understanding, not just recall. "
            f"Return ONLY a JSON array (no markdown, no code fences) with this structure:\n"
            f'[{{"question": "Question text?", "options": ["Option A", "Option B", "Option C", "Option D"], "correct": 0, "explanation": "Why this answer is correct.", "difficulty": "easy|medium|hard"}}]\n'
            f"The 'correct' field is the 0-based index of the correct option.\n\n"
            f"Content:\n{context[:5000]}"
        )
        
        response = self.llm.get_response(
            prompt, 
            mode="Fast Mode", 
            system_prompt="You are an expert quiz generator. Output ONLY valid JSON array. No markdown. No code fences."
        )
        
        try:
            cleaned = response.strip().replace('```json', '').replace('```', '').strip()
            start = cleaned.find('[')
            end = cleaned.rfind(']') + 1
            if start != -1 and end > start:
                questions = json.loads(cleaned[start:end])
                return {"questions": questions}
        except Exception as e:
            print(f"Quiz generation error: {e}")
        
        return {"questions": [{"question": "Error generating quiz", "options": ["Please try again"], "correct": 0, "explanation": "Quiz generation failed.", "difficulty": "easy"}]}

    def get_audio_stream(self, text):
        return generate_audio(text)

    def generate_overview(self, session_id: str = None):
        """Generates a podcast-style audio overview of the entire archive."""
        results = self.memory.retrieve("summary", k=20, session_id=session_id) 
        if not results:
            return None, "No documents found to summarize."
            
        context_text = "\n".join([r['text'] for r in results])
        
        prompt = (
            "You are a podcast host. Generate a 2-minute lively introductory script "
            "summarizing the following source materials for your listeners. "
            "Keep it engaging, highlight key themes, and be conversational.\n\n"
            f"Sources:\n{context_text[:8000]}"
        )
        
        script = self.llm.get_response(prompt, mode="Fast Mode")
        audio_stream = generate_audio(script)
        return audio_stream, script

    def get_memory_stats(self, session_id: str = None):
        return self.memory.get_stats(session_id=session_id)

    def _llm_rerank(self, query: str, chunks: list, top_k: int = 5) -> list:
        """Reranks retrieved chunks using LLM scoring to select the best context."""
        chunk_text = ""
        # Cap chunks and max len to save tokens! Groq 429 prevention.
        chunks_to_rank = chunks[:10]
        for i, c in enumerate(chunks_to_rank):
            chunk_text += f"[{i}] {c['text'][:400]}...\n\n"
            
        prompt = f"""
        Rank these chunks by relevance to the query. 
        Return ONLY a JSON list of the {top_k} most relevant chunk indices, ordered by relevance (e.g., [3, 0, 1, 4, 2]).

        Query: {query}
        
        Chunks:
        {chunk_text}
        """
        
        resp = self.llm.get_response(prompt, mode="Fast Mode", system_prompt="You are a strict reranking AI. Output ONLY a valid JSON array of integers.")
        
        try:
            start = resp.find('[')
            end = resp.rfind(']') + 1
            if start != -1 and end != -1:
                indices = json.loads(resp[start:end])
                reranked = []
                # Ensure valid indices and no duplicates
                seen = set()
                for idx in indices:
                    if isinstance(idx, int) and idx >= 0 and idx < len(chunks) and idx not in seen:
                        reranked.append(chunks[idx])
                        seen.add(idx)
                if reranked:
                    return reranked
        except Exception as e:
            print(f"Reranking JSON parse failed: {e}")
            pass
            
        # Fallback to nearest neighbor FAISS distance (which is already sorted)
        return chunks[:top_k]

    def get_graph(self):
        return self.graph.graph
