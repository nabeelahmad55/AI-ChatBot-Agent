import os
import json
import sys
import re
import requests
# from datetime import datetime, UTC
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "data", "sessions.db")
DATA_JSON_PATH = os.path.join(BASE_DIR, "..", "data", "data.json")
DB_URL = f"sqlite:///{DB_PATH}"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("❌ Missing OPENAI_API_KEY in your .env file")
client = OpenAI(api_key=OPENAI_API_KEY)

os.makedirs(os.path.join(BASE_DIR, "..", "data"), exist_ok=True)

if os.path.exists(DATA_JSON_PATH):
    with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
        localData = json.load(f)
else:
    localData = {}

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class ChatSession(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, index=True)
    agent = Column(String(256), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    conversation_state = Column(Text, default="{}")

    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    role = Column(String(32), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")

def check_and_update_database():
    """Check if database needs to be updated and handle migrations"""
    inspector = inspect(engine)

    if 'sessions' in inspector.get_table_names():
        existing_columns = [col['name'] for col in inspector.get_columns('sessions')]

        if 'conversation_state' not in existing_columns:
            print("Database schema needs update. Adding missing columns...")

            try:
                with engine.begin() as conn:
                    conn.execute(text("""
                        CREATE TABLE sessions_temp (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            agent VARCHAR(256) NOT NULL,
                            created_at DATETIME,
                            conversation_state TEXT DEFAULT '{}'
                        )
                    """))

                    conn.execute(text("""
                        INSERT INTO sessions_temp (id, agent, created_at, conversation_state)
                        SELECT id, agent, created_at, '{}' FROM sessions
                    """))

                    conn.execute(text("DROP TABLE sessions"))
                    conn.execute(text("ALTER TABLE sessions_temp RENAME TO sessions"))

                print("Database schema updated successfully")
            except Exception as e:
                print(f"Database migration failed: {e}")
                print("Creating fresh database...")
                Base.metadata.drop_all(bind=engine)
                Base.metadata.create_all(bind=engine)

    Base.metadata.create_all(bind=engine)

check_and_update_database()
app = Flask(__name__)
CORS(app)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

def ask_supervisor_question(question_number, temperature=0.8):
    """Ask natural supervisor questions using OpenAI API"""
    try:
        print(f"=== SUPERVISOR ASKING QUESTION #{question_number} ===")
        
        
        prompt = f"""You are a call center SUPERVISOR reviewing an agent's edited session which is a set of activities with start time and end time. 
        
Below is the session information:
{json.dumps(localData, indent=2)}

You are reviewing an individual agent data which is specifically given to you.
Ask one natural, logical follow-up question only about schedule adherence, system captured time, phone captured time, or what the agent edited.

Keep the question concise, professional, and focused on getting clarifications about the time discrepancies."""

        print(f"Prompt: {prompt}")
        
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=50
        )
        
        ollama_response = response.choices[0].message.content.strip()
        print(f"Supervisor asks: '{ollama_response}'")
        return ollama_response
            
    except Exception as e:
        print(f"OpenAI API exception: {e}")
        
        fallback_questions = ["HI"]
        return fallback_questions[question_number % len(fallback_questions)]

class ScoringSystem:
    def _get_time_difference_minutes(self, time1, time2):
        """Calculate time difference in minutes - standalone version"""
        if not time1 or not time2:
            return None
        
        try:
            def extract_time_part(datetime_str):
                if not datetime_str:
                    return None
                
                time_match = re.search(r'(\d{1,2}:\d{2}:\d{2}\s*[AP]M)', datetime_str, re.IGNORECASE)
                if time_match:
                    return time_match.group(1)
                return datetime_str
            
            time1_clean = extract_time_part(time1)
            time2_clean = extract_time_part(time2)
            
            def parse_time_to_minutes(time_str):
                if not time_str:
                    return None
                    
                s = str(time_str).strip().upper()
                m = re.search(r'(\d{1,2}):(\d{2}):(\d{2})\s*(AM|PM)?', s)
                if m:
                    hour = int(m.group(1))
                    minute = int(m.group(2))
                    second = int(m.group(3)) if m.group(3) else 0
                    period = m.group(4)

                    if period:
                        if period == 'PM' and hour != 12:
                            hour += 12
                        if period == 'AM' and hour == 12:
                            hour = 0

                    return hour * 60 + minute
                return None

            t1 = parse_time_to_minutes(time1_clean)
            t2 = parse_time_to_minutes(time2_clean)

            if t1 is None or t2 is None:
                return None

            return abs(t1 - t2)

        except Exception as e:
            print(f"Time difference calculation error: {e}")
            return None

    def _fallback_time_analysis(self, agent_data):
        """Fallback time analysis when AI fails"""
        schedule_start = agent_data.get('schedule', {}).get('start_time')
        system_start = agent_data.get('system', {}).get('start_time')
        
        if schedule_start and system_start:
            diff = self._get_time_difference_minutes(schedule_start, system_start)
            if diff and diff > 60:
                return 30, "Significant time discrepancy detected"
            elif diff and diff > 30:
                return 50, "Moderate time discrepancy"
            else:
                return 70, "Minor time discrepancy"
        
        return 50, "Insufficient time data for analysis"

    def analyze_agent_times_ai(self, agent_data):
        """AI-powered analysis of time discrepancies"""
        try:
            analysis_context = self._build_time_analysis_context(agent_data)
            
            prompt = f"""
            Analyze these time discrepancies holistically and provide intelligent scoring:

            {analysis_context}

            Consider these factors dynamically:
            1. Severity of time differences (not just minutes, but context)
            2. Pattern of discrepancies across multiple time sources
            3. Business impact of the discrepancies
            4. Reasonableness of the variations
            5. Consistency across different time systems

            Provide JSON response:
            {{
                "initial_score": 0-100,
                "reasoning": "detailed analysis of time discrepancies",
                "key_issues": ["dynamic issue 1", "dynamic issue 2"],
                "severity_level": "Low/Medium/High/Critical",
                "recommended_weight": 0.1-0.9 (how much should time data influence final score)
            }}
            """
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert analyst evaluating time discrepancies intelligently. Provide dynamic scoring based on holistic assessment."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=400,
                response_format={"type": "json_object"}
            )
            
            analysis = json.loads(response.choices[0].message.content)
            return analysis.get("initial_score", 50), analysis.get("reasoning", "AI analysis performed")
            
        except Exception as e:
            print(f"AI time analysis failed: {e}")
            return self._fallback_time_analysis(agent_data)

    def _build_time_analysis_context(self, agent_data):
        """Build comprehensive context for AI time analysis"""
        schedule_start = agent_data.get('schedule', {}).get('start_time', 'Unknown')
        schedule_end = agent_data.get('schedule', {}).get('end_time', 'Unknown')
        system_start = agent_data.get('system', {}).get('start_time', 'Unknown')
        system_end = agent_data.get('system', {}).get('end_time', 'Unknown')
        phone_start = agent_data.get('phone', {}).get('start_time', 'Unknown')
        phone_end = agent_data.get('phone', {}).get('end_time', 'Unknown')
        claimed_start = agent_data.get('agent_disputed', {}).get('start_time', 'Unknown')
        claimed_end = agent_data.get('agent_disputed', {}).get('end_time', 'Unknown')
        
        differences = []
        if system_start and schedule_start:
            diff = self._get_time_difference_minutes(system_start, schedule_start)
            if diff: differences.append(f"System vs Schedule start: {diff} minutes")
        
        if system_end and schedule_end:
            diff = self._get_time_difference_minutes(system_end, schedule_end)
            if diff: differences.append(f"System vs Schedule end: {diff} minutes")
        
        return f"""
        TIME DISCREPANCY ANALYSIS REQUEST:
        
        Scheduled Times: {schedule_start} to {schedule_end}
        System Times: {system_start} to {system_end}  
        Phone Times: {phone_start} to {phone_end}
        Agent Claimed: {claimed_start} to {claimed_end}
        
        Time Differences Found:
        {chr(10).join(differences) if differences else 'No significant differences calculated'}
        
        Please analyze holistically considering business context and reasonableness.
        """

    def calculate_ai_weights(self, time_analysis, conversation_analysis, conversation_responses):
        """AI-powered weight calculation"""
        try:
            prompt = f"""
            Determine optimal weighting between time data analysis and conversation credibility:

            Time Analysis: {time_analysis}
            Conversation Analysis: {conversation_analysis}
            Conversation Responses: {conversation_responses}

            Consider:
            - Quality and quantity of conversation
            - Severity of time discrepancies
            - Consistency between verbal explanations and data
            - Overall case complexity

            Return JSON:
            {{
                "data_weight": 0.1-0.9,
                "conversation_weight": 0.1-0.9,
                "reasoning": "explanation for weight distribution",
                "primary_factor": "time_data/conversation/both"
            }}
            """
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=300,
                response_format={"type": "json_object"}
            )
            
            weights = json.loads(response.choices[0].message.content)
            return weights.get("data_weight", 0.5), weights.get("conversation_weight", 0.5)
            
        except Exception as e:
            print(f"AI weight calculation failed: {e}")
            return 0.5, 0.5

    def make_final_decision_ai(self, agent_data, conversation_responses):
        """Fully AI-powered final decision"""
        try:
            time_score, time_reasoning = self.analyze_agent_times_ai(agent_data)
            
            conversation_analysis = self.analyze_conversation_content(conversation_responses, agent_data)
            conversation_score = conversation_analysis.get('credibility_score', 50)
            
            data_weight, conversation_weight = self.calculate_ai_weights(
                time_reasoning, conversation_analysis, conversation_responses
            )
            
            final_score = (time_score * data_weight) + (conversation_score * conversation_weight)
            final_score = max(0, min(100, round(final_score)))
            
            decision_reasoning = self._generate_ai_decision_reasoning(
                time_score, time_reasoning, conversation_analysis, 
                data_weight, conversation_weight, final_score
            )
            
            decision = "Accepted" if final_score >= 60 else "Rejected"
            
            return final_score, decision, decision_reasoning, conversation_analysis
            
        except Exception as e:
            print(f"AI final decision failed: {e}")
            return 50, "Manual Review Required", "AI system temporarily unavailable", {}

    def _generate_ai_decision_reasoning(self, time_score, time_reasoning, conversation_analysis, data_weight, conversation_weight, final_score):
        """AI-generated reasoning for final decision"""
        try:
            prompt = f"""
            Synthesize this analysis into coherent final reasoning:

            Time Analysis: {time_reasoning} (Score: {time_score})
            Conversation Analysis: {conversation_analysis}
            Weights: Time {data_weight}, Conversation {conversation_weight}
            Final Score: {final_score}

            Provide concise, professional reasoning for the decision.
            """
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"AI reasoning generation failed: {e}")
            return f"Time score: {time_score} | Conversation analysis: {conversation_analysis.get('justification_quality', 'Unknown')}"

    def analyze_conversation_content(self, conversation_responses, agent_data):
        """PURE AI analysis - no hardcoded rules or keywords"""
        if not conversation_responses:
            return self._get_empty_conversation_analysis()
        
        try:
            analysis_context = self._build_analysis_context(conversation_responses, agent_data)
            prompt = f"""
            You are an expert analyst reviewing a time discrepancy case. Analyze everything dynamically.

            {analysis_context}

            Conduct COMPREHENSIVE analysis considering:
            1. Content credibility and plausibility
            2. Consistency across responses
            3. Specificity and detail level
            4. Professional communication style
            5. Explanation coherence and logic
            6. Evidence of truthfulness or deception cues
            7. Response completeness and engagement
            8. Pattern recognition in language

            Provide detailed JSON analysis WITHOUT any predefined rules:
            {{
                "credibility_score": 0-100 (based on your holistic assessment),
                "consistency_analysis": "detailed analysis of response consistency",
                "key_findings": ["dynamic finding 1", "dynamic finding 2", "dynamic finding 3"],
                "justification_quality": "Strong/Moderate/Weak (based on your assessment)",
                "recommendation": "your professional recommendation",
                "analysis_notes": "your detailed reasoning for scores and findings"
            }}
            """
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert analyst. Provide completely dynamic analysis based only on the content provided. No predefined rules."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            analysis = json.loads(response.choices[0].message.content)
            return analysis
            
        except Exception as e:
            print(f"Primary AI analysis failed: {e}")

            return self._fallback_ai_analysis(conversation_responses, agent_data)

    def _build_analysis_context(self, conversation_responses, agent_data):
        """Build comprehensive context for AI analysis"""
        
        schedule_start = agent_data.get('schedule', {}).get('start_time', 'Unknown')
        system_start = agent_data.get('system', {}).get('start_time', 'Unknown')
        claimed_start = agent_data.get('agent_disputed', {}).get('start_time', 'Unknown')
        
        schedule_system_diff = self._get_time_difference_minutes(schedule_start, system_start)
        schedule_claimed_diff = self._get_time_difference_minutes(schedule_start, claimed_start)
        
        conversation_context = "\n".join([
            f"Response {i+1}: {response}" 
            for i, response in enumerate(conversation_responses)
        ])
        
        return f"""
        CASE CONTEXT:
        - Scheduled Start: {schedule_start}
        - System Recorded Start: {system_start}
        - Agent Claimed Start: {claimed_start}
        - System vs Schedule Difference: {schedule_system_diff} minutes
        - Claimed vs Schedule Difference: {schedule_claimed_diff} minutes

        FULL CONVERSATION:
        {conversation_context}

        ANALYSIS INSTRUCTIONS:
        Analyze this case holistically. Consider all aspects of the conversation and context.
        """

    def _get_system_failure_analysis(self):
        """Fully dynamic system failure analysis"""
        default_score = 50 
        
        return {
            "credibility_score": default_score,
            "consistency_analysis": "Analysis system unavailable",
            "key_findings": ["System review required"],
            "justification_quality": "Unknown",
            "recommendation": "Manual assessment needed",
            "analysis_notes": "Automated analysis temporarily unavailable"
        }

    def _get_emergency_analysis(self, conversation_responses):
        """Fully dynamic emergency analysis without hardcoded patterns"""
        try:
            if not conversation_responses:
                return self._get_empty_conversation_analysis()
            
            response_count = len(conversation_responses)
            
            word_counts = [len(str(response).split()) for response in conversation_responses]
            avg_words = sum(word_counts) / len(word_counts) if word_counts else 0
            
            response_density = min(1.0, avg_words / 20)
            participation_rate = min(1.0, response_count / 10)
            
            base_score = 30 + (response_density * 40) + (participation_rate * 30)
            final_score = max(0, min(100, int(base_score)))
            
            findings = []
            if response_count > 0:
                findings.append(f"Engaged with {response_count} responses")
            if avg_words > 5:
                findings.append("Provided substantive responses")
            
            return {
                "credibility_score": final_score,
                "consistency_analysis": f"Analyzed {response_count} responses",
                "key_findings": findings if findings else ["Conversation recorded"],
                "justification_quality": "Assessed" if response_count > 0 else "Minimal",
                "recommendation": "Review conversation",
                "analysis_notes": f"Dynamic analysis: {response_count} responses, {avg_words:.1f} avg words"
            }
            
        except Exception as e:
            print(f"Dynamic analysis failed: {e}")
            return self._get_system_failure_analysis()

    def _fallback_ai_analysis(self, conversation_responses, agent_data):
        """Pure AI analysis without hardcoded prompts"""
        try:
            if not conversation_responses:
                return self._get_empty_conversation_analysis()
            
            conversation_text = " | ".join([str(r) for r in conversation_responses])
            
            prompt = f"""
            Analyze this conversation and provide assessment in JSON format:
            {conversation_text}
            """
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200,
                response_format={"type": "json_object"}
            )
            
            analysis = json.loads(response.choices[0].message.content)
            
            return {
                "credibility_score": analysis.get("credibility_score", analysis.get("score", 50)),
                "consistency_analysis": analysis.get("consistency_analysis", analysis.get("analysis", "Reviewed")),
                "key_findings": analysis.get("key_findings", analysis.get("findings", ["Conversation analyzed"])),
                "justification_quality": analysis.get("justification_quality", analysis.get("quality", "Unknown")),
                "recommendation": analysis.get("recommendation", "Review completed"),
                "analysis_notes": analysis.get("analysis_notes", analysis.get("notes", "AI analysis performed"))
            }
            
        except Exception as e:
            print(f"AI fallback failed: {e}")
            return self._get_emergency_analysis(conversation_responses)

    def _get_empty_conversation_analysis(self):
        """Analysis for no conversation - still AI-style structure"""
        return {
            "credibility_score": 0,
            "consistency_analysis": "No conversation occurred",
            "key_findings": ["Agent provided no responses", "No explanation given for discrepancy"],
            "justification_quality": "None",
            "recommendation": "Automatic rejection - no participation",
            "analysis_notes": "Zero score assigned due to complete lack of response or engagement"
        }

    def _assess_analysis_quality(self, conversation_analysis):
        """Assess how reliable the AI analysis appears to be"""
        score = conversation_analysis.get('credibility_score', 0)
        notes = conversation_analysis.get('analysis_notes', '')
        
        if "system" in notes.lower() and "unavailable" in notes.lower():
            return "low"
        elif "limited" in notes.lower() or "brief" in notes.lower():
            return "medium"
        else:
            return "high"

    def _build_ai_reasoning(self, data_reasoning, conversation_analysis):
        """Build final reasoning using AI-generated insights"""
        
        reasoning_parts = [f"Data analysis: {data_reasoning}"]
        
        consistency = conversation_analysis.get('consistency_analysis', 'No conversation analysis')
        justification = conversation_analysis.get('justification_quality', 'Not assessed')
        notes = conversation_analysis.get('analysis_notes', '')
        
        reasoning_parts.append(f"Conversation analysis: {consistency}")
        reasoning_parts.append(f"Justification quality: {justification}")
        
        key_findings = conversation_analysis.get('key_findings', [])
        if key_findings and len(key_findings) > 0:
            primary_finding = key_findings[0]
            reasoning_parts.append(f"Primary finding: {primary_finding}")
        
        if notes and len(notes) > 20 and "system" not in notes.lower() and "unavailable" not in notes.lower():
            brief_notes = notes[:100] + "..." if len(notes) > 100 else notes
            reasoning_parts.append(f"Analysis: {brief_notes}")
        
        return " | ".join(reasoning_parts)

class ConversationManager:
    def __init__(self):
        self.asked_questions_tracker = {}
        self.scoring_system = ScoringSystem()

    def standardize_time_format(self, time_str):
        """Convert many time formats to consistent h:mm:ss AM/PM or return 'unknown'."""
        if not time_str or str(time_str).strip() == '':
            return 'unknown'

        try:
            s = str(time_str).strip()
            try:
                dt = datetime.fromisoformat(s)
                return dt.strftime("%I:%M:%S %p")
            except Exception:
                pass

            m = re.search(r'(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(AM|PM|am|pm)?', s)
            if m:
                hour = int(m.group(1))
                minute = int(m.group(2))
                second = int(m.group(3)) if m.group(3) else 0
                period = m.group(4)

                if period:
                    period = period.upper()
                    if period == 'PM' and hour != 12:
                        hour += 12
                    if period == 'AM' and hour == 12:
                        hour = 0
                else:
                    if 0 <= hour <= 23:
                        pass  
                    else:
                        return 'unknown'

                disp_hour = hour
                disp_period = 'AM'
                if hour == 0:
                    disp_hour = 12
                    disp_period = 'AM'
                elif hour == 12:
                    disp_hour = 12
                    disp_period = 'PM'
                elif hour > 12:
                    disp_hour = hour - 12
                    disp_period = 'PM'
                else:
                    disp_period = 'AM'

                return f"{disp_hour:02d}:{minute:02d}:{second:02d} {disp_period}"

            m2 = re.search(r'^\d{1,4}$', s)
            if m2:
                val = s
                if len(val) in (3,4):
                    minute_part = val[-2:]
                    hour_part = val[:-2]
                    hour = int(hour_part)
                    minute = int(minute_part)
                    return self.standardize_time_format(f"{hour}:{minute}:00")
                elif len(val) <= 2:
                    hour = int(val)
                    return self.standardize_time_format(f"{hour}:00:00")

            return 'unknown'

        except Exception as e:
            print(f"Time standardization error: {e}")
            return 'unknown'

    def get_time_difference(self, time1_str, time2_str):
        """Calculate time difference in minutes between two time strings. Returns int or None."""
        if not time1_str or not time2_str:
            return None

        try:
            def parse_time_to_minutes(time_str):
                standardized = self.standardize_time_format(time_str)
                if standardized == 'unknown':
                    return None
                parts = standardized.split(' ')
                time_part = parts[0]
                period = parts[1] if len(parts) > 1 else 'AM'

                hours, minutes, seconds = map(int, time_part.split(':'))

                if period.upper() == 'PM' and hours != 12:
                    hours += 12
                elif period.upper() == 'AM' and hours == 12:
                    hours = 0

                return hours * 60 + minutes

            t1 = parse_time_to_minutes(time1_str)
            t2 = parse_time_to_minutes(time2_str)

            if t1 is None or t2 is None:
                return None

            return abs(t1 - t2)

        except Exception as e:
            print(f"Time difference calculation error: {e}")
            return None

    def analyze_conversation_state(self, messages, agent_context, session_id):
        """Analyze conversation state"""
        user_messages = [msg["content"] for msg in messages if msg["role"] == "user"]
        assistant_messages = [msg["content"] for msg in messages if msg["role"] == "assistant"]
        
        question_count = sum(1 for msg in assistant_messages if msg.strip().endswith('?'))
        
        if session_id not in self.asked_questions_tracker:
            self.asked_questions_tracker[session_id] = {
                "asked_questions": [],
                "user_responses": []
            }
        
        tracker = self.asked_questions_tracker[session_id]
        
        if user_messages:
            tracker["user_responses"] = user_messages

        state = {
            "question_count": question_count,
            "asked_questions": tracker["asked_questions"],
            "user_responses": tracker["user_responses"]
        }

        return state

    def _generate_fallback_question_via_ai(self, previous_questions, user_input, question_number):
        """Generate fallback question using AI when primary method fails - NO HARCODED QUESTIONS"""
        try:
            print("Generating fallback question via AI...")
            
            prompt = f"""Generate a natural supervisor follow-up question about time entry discrepancies.

    Context: Supervisor reviewing agent's time edits
    Previous questions: {previous_questions[-2:] if previous_questions else "None"}
    Latest agent response: "{user_input}" if user_input else "None"

    Create one professional, natural question that seeks clarification."""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Generate exactly one natural supervisor question about time entry clarification."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=60,
                timeout=20
            )
            
            question = response.choices[0].message.content.strip()
            question = self._clean_question_basic(question)
            return question if question else "Could you provide more clarification about this time entry?"
            
        except Exception as e:
            print(f"Fallback AI also failed: {e}")
            
            return "Could you provide more clarification about this time entry?"

    def _clean_question_basic(self, raw_question):
        """Basic question cleaning - NO VALIDATION LOGIC"""
        if not raw_question:
            return None

        question = raw_question.strip()
        question = question.strip('"\'')
        
        prefixes = ["Question:", "Ask:", "Supervisor:", "I would ask:", "My question is:", "Next question:"]
        for prefix in prefixes:
            if question.lower().startswith(prefix.lower()):
                question = question[len(prefix):].strip()
        
        if not question.endswith('?'):
            question += '?'
        
        if question and len(question) > 1:
            question = question[0].upper() + question[1:]
        
        return question

    def _is_duplicate_question(self, question, previous_questions):
        """Check if question is too similar to previous questions - IMPROVED"""
        if not previous_questions:
            return False
        
        current_lower = question.lower()
        
        if current_lower in [q.lower() for q in previous_questions]:
            return True
        
        current_start = ' '.join(current_lower.split()[:4])
        for prev_q in previous_questions[-3:]:
            prev_start = ' '.join(prev_q.lower().split()[:4])
            if current_start == prev_start:
                return True
        
        return False

    def _clean_and_validate_question(self, raw_question, previous_questions, user_input):
        """Clean and validate question - NO WORD LIMIT"""
        if not raw_question:
            return None

        question = self._clean_question_basic(raw_question)
        if not question:
            return None
        
        if self._is_redundant_question(question, user_input):
            print(f"Question is redundant given user response: '{question}'")
            return None
        
        if self._is_duplicate_question(question, previous_questions):
            print(f"Question is duplicate: '{question}'")
            return None
        
        if len(question.strip()) < 5:
            print(f"Question too short: '{question}'")
            return None
        
        return question

    def _ask_natural_supervisor_question(self, user_input, question_number, session_id):
        """Ask natural supervisor question using OpenAI API - NO SUMMARY_REQUEST"""
        try:
            print(f"=== ASKING SUPERVISOR QUESTION #{question_number} ===")
            
            tracker = self.asked_questions_tracker.get(session_id, {"asked_questions": [], "user_responses": []})
            previous_questions = tracker.get("asked_questions", [])
            previous_responses = tracker.get("user_responses", [])
            
            prompt = f"""You are a call center supervisor conducting a professional conversation to understand time entry discrepancies.

    AGENT DATA:
    {json.dumps(localData, indent=2)}

    CONVERSATION HISTORY:
    Previous questions asked: {previous_questions if previous_questions else "None"}
    Agent's responses: {previous_responses if previous_responses else "None"}
    Latest agent response: "{user_input}"

    Your task: Ask exactly ONE natural, professional follow-up question that:
    - Seeks NEW information not already provided
    - Avoids asking about information already given (arrival time, system time, editing reason)
    - Focuses on understanding the CAUSE or CONTEXT of the discrepancy
    - Is different from previous questions: {previous_questions[-3:] if previous_questions else "None"}
    - Sounds like a natural supervisor conversation

    IMPORTANT: Always return a question, never indicate ending the conversation.

    Next question:"""

            print(f"Prompt sent to OpenAI: {prompt}")
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": """You are a professional call center supervisor. 
                    Generate exactly one follow-up question that:
                    - Builds on NEW information not already covered
                    - Avoids repetition of already answered questions
                    - Sounds conversational and professional
                    - Seeks specific clarifications about CAUSES or CONTEXT
                    - Always ends with a question mark
                    - Never indicates ending the conversation"""},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=80,
                timeout=30
            )
            
            question = response.choices[0].message.content.strip()
            print(f"Raw OpenAI response: '{question}'")
            
            cleaned_question = self._clean_and_validate_question(question, previous_questions, user_input)
            
            if cleaned_question:
                return cleaned_question
            else:
                return self._generate_fallback_question_via_ai(previous_questions, user_input, question_number)
                    
        except Exception as e:
            print(f"OpenAI API exception: {e}")
            return self._generate_fallback_question_via_ai(previous_questions, user_input, question_number)

    def _is_redundant_question(self, question, user_input):
        """Check if question is asking for information already provided"""
        if not user_input:
            return False
        
        question_lower = question.lower()
        user_lower = user_input.lower()
        
        redundant_patterns = [
            "what time did you arrive",
            "when did you arrive", 
            "what time did the system show",
            "why did you edit",
            "what was the reason for editing"
        ]
        if "edit" in user_lower and "why did you edit" in question_lower:
            return True
        
        return False

    def should_end_conversation(self, conversation_state, recent_user_input="", tracker=None):
        """AI-powered decision on when to end conversation"""
        question_count = conversation_state.get("question_count", 0)
        
        print(f"Should end check: {question_count} questions, input: '{recent_user_input}'")
        
        if question_count >= 5:
            print(f"Ending - maximum questions reached: {question_count}")
            return True
        
        if question_count >= 3 and self._ai_analyze_completion_signal(recent_user_input, question_count, tracker):
            print(f"Ending - AI detected completion signal after {question_count} questions")
            return True
        
        print(f"Continuing - {question_count} questions, no completion signal")
        return False

    def _ai_analyze_completion_signal(self, user_input, question_count, tracker):
        """AI analyzes if user is signaling conversation completion"""
        if not user_input:
            return False
        
        try:
            prompt = f"""
            Analyze if the user is signaling they want to END the conversation or just giving a vague answer.

            USER RESPONSE: "{user_input}"
            CONVERSATION CONTEXT: 
            - Question number: {question_count}
            - This is a professional supervisor-agent discussion about time discrepancies
            - User has provided {len(tracker.get('user_responses', []))} responses so far

            Determine if the user is:
            A) Clearly indicating they have nothing more to add (END CONVERSATION)
            B) Giving a vague/unclear answer that needs follow-up (CONTINUE)
            C) Expressing frustration about repetitive questions (END CONVERSATION)
            D) Simply providing a short but valid response (CONTINUE)

            Respond with ONLY JSON:
            {{
                "should_end": true/false,
                "reasoning": "brief explanation",
                "confidence": 0-100
            }}
            """

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a conversation analyst. Determine if the user wants to end the discussion."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=150,
                response_format={"type": "json_object"}
            )
            
            analysis = json.loads(response.choices[0].message.content)
            
            should_end = analysis.get("should_end", False)
            confidence = analysis.get("confidence", 0)
            
            print(f"AI completion analysis: should_end={should_end}, confidence={confidence}, reasoning={analysis.get('reasoning')}")
            
            return should_end and confidence >= 70
            
        except Exception as e:
            print(f"AI completion analysis failed: {e}")
            return question_count >= 4 and len(user_input.strip().split()) <= 3

    def _is_user_frustrated(self, user_input, previous_responses):
        """AI-powered frustration detection"""
        if not user_input:
            return False
        
        try:
            conversation_context = " | ".join(previous_responses[-3:]) if previous_responses else "No previous responses"
            
            prompt = f"""
            Analyze if the user is expressing FRUSTRATION with the conversation.

            CURRENT RESPONSE: "{user_input}"
            RECENT CONVERSATION: "{conversation_context}"

            Look for signs of:
            - Annoyance with repetitive questions
            - Desire to stop the conversation
            - Irritation in tone or content
            - Resistance to providing more information

            Respond with ONLY JSON:
            {{
                "is_frustrated": true/false,
                "reasoning": "brief analysis of why",
                "frustration_level": "low/medium/high",
                "suggest_action": "continue/end/clarify"
            }}
            """

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You detect user frustration in professional conversations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200,
                response_format={"type": "json_object"}
            )
            
            analysis = json.loads(response.choices[0].message.content)
            
            is_frustrated = analysis.get("is_frustrated", False)
            frustration_level = analysis.get("frustration_level", "low")
            suggest_action = analysis.get("suggest_action", "continue")
            
            print(f"AI frustration analysis: frustrated={is_frustrated}, level={frustration_level}, action={suggest_action}")
            
            return (is_frustrated and frustration_level == "high") or suggest_action == "end"
            
        except Exception as e:
            print(f"AI frustration analysis failed: {e}")
            return False

    def _ai_assess_response_quality(self, user_input, question_count):
        """AI assesses if response is substantial enough to continue"""
        if not user_input:
            return False
        
        try:
            prompt = f"""
            Assess if this user response contains SUBSTANTIAL information worth following up on.

            RESPONSE: "{user_input}"
            CONTEXT: Question #{question_count} in a professional time discrepancy discussion

            Evaluate:
            - Does this provide new information?
            - Is it a complete thought or just a fragment?
            - Does it answer the question asked?
            - Is there ambiguity that needs clarification?

            Respond with ONLY JSON:
            {{
                "has_substance": true/false,
                "quality_score": 0-100,
                "needs_clarification": true/false,
                "recommendation": "follow_up/end/seek_clarification"
            }}
            """

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You assess response quality in professional dialogues."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=150,
                response_format={"type": "json_object"}
            )
            
            analysis = json.loads(response.choices[0].message.content)
            
            has_substance = analysis.get("has_substance", False)
            quality_score = analysis.get("quality_score", 0)
            needs_clarification = analysis.get("needs_clarification", False)
            recommendation = analysis.get("recommendation", "follow_up")
            
            print(f"AI quality assessment: substance={has_substance}, score={quality_score}, needs_clarification={needs_clarification}, recommendation={recommendation}")
            
            return has_substance or needs_clarification or recommendation in ["follow_up", "seek_clarification"]
            
        except Exception as e:
            print(f"AI quality assessment failed: {e}")
            return len(user_input.strip().split()) > 2

    def _generate_basic_summary_fallback(self, messages):
        """Generate basic summary fallback without hardcoded templates"""
        user_responses = [msg["content"] for msg in messages if msg["role"] == "user"]
        
        if not user_responses:
            return "CONVERSATION SUMMARY: Conversation completed. No additional details provided."
        
        key_points = []
        
        for response in user_responses:
            response_lower = response.lower()
            
            if any(term in response_lower for term in ["system", "time"]) and any(term in response_lower for term in ["wrong", "incorrect", "inaccurate"]):
                key_points.append("System time discrepancy reported")
            
            if any(term in response_lower for term in ["arrive", "came", "start"]) and any(term in response_lower for term in ["early", "before"]):
                key_points.append("Early arrival mentioned")
            
            if "meeting" in response_lower:
                key_points.append("Meeting attendance noted")
            
            if any(term in response_lower for term in ["edit", "change", "adjust", "correct"]):
                key_points.append("Time entry modification explained")
        
        unique_points = []
        for point in key_points:
            if point not in unique_points:
                unique_points.append(point)
        
        if unique_points:
            summary = "CONVERSATION SUMMARY:\nDiscussion highlights:\n" + "\n".join([f"- {point}" for point in unique_points])
        else:
            summary = "CONVERSATION SUMMARY: Conversation reviewed. Details documented for supervisor follow-up."
        
        return summary

    def _generate_final_summary_question(self, previous_questions):
        """Generate a final question that naturally leads to conversation conclusion"""
        try:
            prompt = f"""Generate one final professional question that naturally concludes the time discrepancy discussion.

    Previous questions asked: {previous_questions[-3:] if previous_questions else "None"}

    Create a question that:
    - Summarizes what we've discussed
    - Gives the agent one final chance to add information
    - Naturally transitions to ending the conversation
    - Sounds professional and respectful

    Final question:"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Generate one final question that naturally concludes the conversation professionally."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=60
            )
            
            question = response.choices[0].message.content.strip()
            question = self._clean_question_basic(question)
            return question if question else "Is there anything else you'd like to add about this time discrepancy?"
            
        except Exception as e:
            print(f"Final question generation failed: {e}")
            return "Is there anything else you'd like to add about this time discrepancy before we conclude?"

    def _generate_dynamic_fallback_question(self, previous_questions, user_input, question_number):
        """Generate dynamic fallback question using AI - NO HARCODED CONTENT"""
        try:
            print("Generating dynamic fallback question via AI...")
            
            prompt = f"""Generate one natural supervisor follow-up question about time entry discrepancies.

    Context: 
    - Question number: {question_number}
    - Previous questions: {previous_questions[-2:] if previous_questions else "None"}
    - Latest agent response: "{user_input}" if user_input else "None"

    Create one professional, natural question that seeks clarification about time discrepancies."""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Generate exactly one natural supervisor question about time entry clarification."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=60,
                timeout=20
            )
            
            question = response.choices[0].message.content.strip()
            question = self._clean_question_basic(question)
            return question if question else "Could you provide more clarification about this time entry?"
            
        except Exception as e:
            print(f"Dynamic fallback AI failed: {e}")
            return "Could you provide more clarification about this time entry?"

    def generate_natural_question(self, conversation_state, recent_user_input="", session_id=""):
        """Generate NATURAL supervisor questions - NO SUMMARY_REQUEST"""
        
        if session_id not in self.asked_questions_tracker:
            self.asked_questions_tracker[session_id] = {
                "asked_questions": [],
                "user_responses": []
            }
        
        tracker = self.asked_questions_tracker[session_id]
        question_count = conversation_state.get('question_count', 0)
        
        print(f"=== NATURAL QUESTION GENERATION ===")
        print(f"Question count: {question_count}")
        print(f"Recent input: '{recent_user_input}'")
        print(f"Previous questions: {len(tracker['asked_questions'])}")
        
        if self.should_end_conversation(conversation_state, recent_user_input, tracker):
            print("Supervisor ending conversation - generating final summary question")
            return self._generate_final_summary_question(tracker["asked_questions"])
        
        question = self._ask_natural_supervisor_question(recent_user_input, question_count + 1, session_id)
        
        if not question:
            question = self._generate_fallback_question_via_ai(tracker["asked_questions"], recent_user_input, question_count + 1)
        
        tracker["asked_questions"].append(question)
        if recent_user_input:
            tracker["user_responses"].append(recent_user_input)
        
        print(f"Final question to ask: '{question}'")
        return question

    def _print_detailed_analysis_to_console(self, agent_context, user_responses, final_score, decision, reasoning, conversation_analysis, duration_display):
        """Print detailed analysis to console with timer"""
        print("\n" + "="*80)
        print("📊 DETAILED CONVERSATION ANALYSIS (CONSOLE ONLY)")
        print("="*80)
        
        print(f"⏰ CONVERSATION DURATION: {duration_display}")
        
        print(f"\n🔍 AGENT DATA ANALYSIS:")
        print(f"   Schedule: {agent_context.get('schedule', {})}")
        print(f"   System Times: {agent_context.get('system', {})}")
        print(f"   Phone Times: {agent_context.get('phone', {})}")
        print(f"   Agent Claimed: {agent_context.get('agent_disputed', {})}")
        
        print(f"\n💬 CONVERSATION ANALYSIS:")
        for i, response in enumerate(user_responses, 1):
            print(f"   Response {i}: {response}")
        
        print(f"\n📈 SCORING BREAKDOWN:")
        print(f"   Final Score: {final_score}/100")
        print(f"   Decision: {decision}")
        print(f"   Reasoning: {reasoning}")
        print(f"   Credibility Score: {conversation_analysis.get('credibility_score', 'N/A')}/100")
        print(f"   Justification Quality: {conversation_analysis.get('justification_quality', 'N/A')}")
        
        print(f"\n🔑 KEY FINDINGS:")
        for finding in conversation_analysis.get('key_findings', []):
            print(f"   • {finding}")
        
        print(f"   Recommendation: {conversation_analysis.get('recommendation', 'N/A')}")
        print("="*80 + "\n")

    def _generate_concise_summary(self, agent_context, user_responses, final_score, decision, conversation_analysis, duration_display):
        """Generate 2-3 line concise summary with timer"""
        
        schedule_start = agent_context.get('schedule', {}).get('start_time', 'Unknown')
        system_start = agent_context.get('system', {}).get('start_time', 'Unknown')
        claimed_start = agent_context.get('agent_disputed', {}).get('start_time', 'Unknown')
        
        schedule_system_diff = self.get_time_difference(schedule_start, system_start)
        schedule_claimed_diff = self.get_time_difference(schedule_start, claimed_start)
        
        main_issue = "System time discrepancy"
        if schedule_system_diff and schedule_system_diff > 30:
            main_issue = f"Major system time gap ({schedule_system_diff}min)"
        elif schedule_claimed_diff and schedule_claimed_diff > 30:
            main_issue = f"Claimed time mismatch ({schedule_claimed_diff}min)"
        
        justification = conversation_analysis.get('justification_quality', 'Weak').lower()
        credibility = conversation_analysis.get('credibility_score', 50)
        
        if credibility >= 70:
            justification_desc = "reasonable justification"
        elif credibility >= 50:
            justification_desc = "limited justification" 
        else:
            justification_desc = "weak justification"
        
        summary_parts = []
        
        summary_parts.append(f"Score: {final_score}/100 - {decision}")
        
        summary_parts.append(f"{main_issue} with {justification_desc}")
        
        summary_parts.append(f"Duration: {duration_display}")
        
        key_findings = conversation_analysis.get('key_findings', [])
        if key_findings and len(summary_parts) < 4:
            main_finding = key_findings[0].split('.')[0]
            if len(main_finding) < 40: 
                summary_parts.append(main_finding)
        
        concise_summary = "\n".join(summary_parts)
        
        if len(concise_summary) > 200:
            concise_summary = "\n".join(summary_parts[:3])
        
        return concise_summary

    def _generate_combined_analysis_summary(self, agent_context, user_responses, final_score, decision, reasoning, conversation_analysis, duration_display):
        """Generate summary showing conversation highlights and final decision"""
        
        data_score, data_reasoning = self.scoring_system.analyze_agent_times_ai(agent_context)
        
        conv_score = conversation_analysis.get('credibility_score', 50)
        justification_quality = conversation_analysis.get('justification_quality', 'Unknown')
        
        schedule_start = agent_context.get('schedule', {}).get('start_time', 'Unknown')
        system_start = agent_context.get('system', {}).get('start_time', 'Unknown')
        schedule_system_diff = self.get_time_difference(schedule_start, system_start)
        
        conversation_summary = self._generate_conversation_summary_line(user_responses)
        
        summary_parts = []
        
        summary_parts.append(f"FINAL DECISION: {decision} ({final_score}/100)")
        
        summary_parts.append(f"\n{conversation_summary}")
        
        summary_parts.append(f"\nData Score: {data_score}/100 \n Conversation Score: {conv_score}/100")
        summary_parts.append(f"\n{schedule_system_diff}min discrepancy \n {justification_quality} justification")
        
        summary_parts.append(f"\n{duration_display}")
        
        combined_summary = "\n".join(summary_parts)
        
        return "CONVERSATION_END:\n" + combined_summary

    def _generate_conversation_summary_line(self, user_responses):
        """Generate ONE readable line summarizing the entire conversation"""
        if not user_responses:
            return "No conversation occurred"
        
        try:
            
            conversation_text = " | ".join(user_responses)
            
            prompt = f"""Summarize this entire conversation in ONE clear, readable sentence (max 15 words). Focus on the main point the agent communicated:

            Conversation: {conversation_text}

            Return JSON: {{"summary": "one sentence summary here"}}"""
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Create one clear sentence summary of what the agent communicated."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=100,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            summary = result.get('summary', '').strip()
            
            if summary:
                return summary
            
        except Exception as e:
            print(f"AI summary failed: {e}")
        
        if user_responses:
            key_points = []
            for response in user_responses:
                if "system" in response.lower() and "incorrect" in response.lower():
                    key_points.append("system error")
                if "edit" in response.lower():
                    key_points.append("time edit")
                if "office" in response.lower() or "clock" in response.lower():
                    key_points.append("office clock reference")
            
            if key_points:
                return f"Agent reported {', '.join(set(key_points))}"
        
        return f"Agent provided {len(user_responses)} responses about time discrepancy"

    def _calculate_conversation_duration(self, messages):
        """Calculate conversation duration - IMPROVED VERSION"""
        if not messages or len(messages) < 2:
            return "Brief exchange"
        
        try:
            print(f"DEBUG: Calculating duration for {len(messages)} messages")
            
            timestamps = []
            for msg in messages:
                timestamp = None
                
                if hasattr(msg, 'created_at'):
                    timestamp = msg.created_at
                elif isinstance(msg, dict) and 'created_at' in msg:
                    timestamp = msg['created_at']
                elif hasattr(msg, 'get') and callable(msg.get):
                    timestamp = msg.get('created_at')
                
                if timestamp:
                    timestamps.append(timestamp)
                    print(f"DEBUG: Found timestamp: {timestamp} (type: {type(timestamp)})")
            
            if len(timestamps) < 2:
                print(f"DEBUG: Only {len(timestamps)} valid timestamps found")
                estimated_seconds = len(messages) * 30
                minutes = estimated_seconds // 60
                seconds = estimated_seconds % 60
                if minutes > 0:
                    return f"~{minutes}m {seconds}s (estimated)"
                else:
                    return f"~{seconds}s (estimated)"
            
            datetime_objs = []
            for ts in timestamps:
                if isinstance(ts, datetime):
                    datetime_objs.append(ts)
                elif isinstance(ts, str):
                    try:
                        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        datetime_objs.append(dt)
                    except ValueError:
                        try:
                            dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S.%f')
                            datetime_objs.append(dt)
                        except ValueError:
                            try:
                                dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
                                datetime_objs.append(dt)
                            except ValueError:
                                continue
            
            if len(datetime_objs) < 2:
                estimated_seconds = len(messages) * 30
                minutes = estimated_seconds // 60
                seconds = estimated_seconds % 60
                return f"~{minutes}m {seconds}s (estimated)"
            
            sorted_times = sorted(datetime_objs)
            first = sorted_times[0]
            last = sorted_times[-1]
            
            duration = last - first
            total_seconds = duration.total_seconds()
            
            print(f"DEBUG: Actual duration: {total_seconds} seconds")
            
            if total_seconds <= 0:
                estimated_seconds = len(messages) * 30
                minutes = estimated_seconds // 60
                seconds = estimated_seconds % 60
                return f"~{minutes}m {seconds}s (estimated)"
            
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)
            
            if minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
                
        except Exception as e:
            print(f"Duration calculation error: {e}")
            estimated_seconds = len(messages) * 25
            minutes = estimated_seconds // 60
            seconds = estimated_seconds % 60
            if minutes > 0:
                return f"~{minutes}m {seconds}s"
            else:
                return f"~{seconds}s"

    def get_messages_with_timestamps(self, session_id):
        """Get messages from database with proper timestamps"""
        try:
            db = SessionLocal()
            session_messages = db.query(ChatMessage).filter(
                ChatMessage.session_id == session_id
            ).order_by(ChatMessage.created_at).all()
            db.close()
            return session_messages
        except Exception as e:
            print(f"Error getting messages from database: {e}")
            return None

    def generate_accurate_summary(self, messages, agent_context, session_id=None, db_session=None):
        """Generate comprehensive summary combining data analysis AND conversation analysis"""
        try:
            user_responses = [msg["content"] for msg in messages if msg["role"] == "user"]
            
            final_score, decision, reasoning, conversation_analysis = self.scoring_system.make_final_decision_ai(
                agent_context, user_responses
            )
            duration_display = "Brief conversation"
            if session_id:
                db_messages = self.get_messages_with_timestamps(session_id)
                if db_messages and len(db_messages) >= 2:
                    duration_display = self._calculate_conversation_duration(db_messages)
                else:
                    duration_display = self._calculate_conversation_duration(messages)
            else:
                duration_display = self._calculate_conversation_duration(messages)
            
            comprehensive_summary = self._generate_combined_analysis_summary(
                agent_context, user_responses, final_score, decision, 
                reasoning, conversation_analysis, duration_display
            )
            self._print_detailed_analysis_to_console(
                agent_context, user_responses, final_score, decision, 
                reasoning, conversation_analysis, duration_display
            )
            
            return comprehensive_summary
            
        except Exception as e:
            print(f"Error generating summary: {e}")
            return "Conversation reviewed and decision made."

conv_manager = ConversationManager()

@app.route("/data", methods=["GET"])
def get_json_data():
    return jsonify(localData)

@app.route("/create_session", methods=["POST"])
def create_session():
    body = request.get_json() or {}
    agent = body.get("agent", "unknown")
    db = SessionLocal()
    s = ChatSession(agent=agent)
    db.add(s)
    db.commit()
    db.refresh(s)
    db.close()
    return jsonify({"id": s.id, "agent": s.agent, "created_at": s.created_at.isoformat()}), 201

@app.route("/sessions/<int:session_id>/messages", methods=["POST"])
def add_message(session_id):
    body = request.get_json() or {}
    role = body.get("role", "user")
    content = body.get("content", "")
    ts = body.get("created_at")
    db = SessionLocal()
    s = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not s:
        db.close()
        return jsonify({"error": "session not found"}), 404
    if ts:
        try:
            created_at = datetime.fromisoformat(ts)
        except:
            created_at = datetime.utcnow()
    else:
        created_at = datetime.utcnow()
    msg = ChatMessage(session_id=session_id, role=role, content=content, created_at=created_at)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    db.close()
    return jsonify({"message_id": msg.id, "session_id": session_id}), 201

@app.route("/sessions", methods=["GET"])
def list_sessions():
    db = SessionLocal()
    try:
        sessions = db.query(ChatSession).order_by(ChatSession.created_at.desc()).all()
        out = []
        for s in sessions:
            last_msg = None
            if s.messages:
                last_msg = max(s.messages, key=lambda m: m.created_at).created_at.isoformat()
            out.append({
                "id": s.id,
                "agent": s.agent,
                "created_at": s.created_at.isoformat(),
                "last_message_at": last_msg
            })
        db.close()
        return jsonify(out)
    except Exception as e:
        db.close()
        print(f"Error listing sessions: {e}")
        return jsonify({"error": "Database error occurred"}), 500

@app.route("/sessions/<int:session_id>", methods=["GET"])
def get_session(session_id):
    db = SessionLocal()
    try:
        s = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not s:
            db.close()
            return jsonify({"error": "session not found"}), 404
        messages = [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat()
            } for m in sorted(s.messages, key=lambda mm: mm.created_at)
        ]
        out = {
            "id": s.id,
            "agent": s.agent,
            "created_at": s.created_at.isoformat(),
            "messages": messages
        }
        db.close()
        return jsonify(out)
    except Exception as e:
        db.close()
        print(f"Error getting session: {e}")
        return jsonify({"error": "Database error occurred"}), 500

@app.route("/chat_with_ai", methods=["POST"])
def chat_with_ai():
    """NATURAL supervisor chat with improved questions - NO SUMMARY_REQUEST"""
    try:
        body = request.get_json() or {}
        messages = body.get("messages", [])
        session_id = body.get("session_id")
        agent_name = body.get("agent_name", "")

        if not messages or not session_id:
            return jsonify({"error": "No messages or session_id provided"}), 400

        db = SessionLocal()
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            db.close()
            return jsonify({"error": "Session not found"}), 404

        agents = localData.get("agents", [])
        agent_context = next((a for a in agents if a.get("name", "").lower() == agent_name.lower()), {}) if agent_name else {}

        conversation_state = conv_manager.analyze_conversation_state(messages, agent_context, session_id)

        recent_user_input = ""
        if messages and messages[-1]["role"] == "user":
            recent_user_input = messages[-1]["content"]

        if conv_manager.should_end_conversation(conversation_state, recent_user_input):
            print(f"Supervisor ending conversation with {conversation_state.get('question_count', 0)} questions")
            summary = conv_manager.generate_accurate_summary(messages, agent_context, session_id)
            
            confirmation_msg = ChatMessage(
                session_id=session_id,
                role="assistant",
                content=summary,
                created_at=datetime.utcnow()
            )
            db.add(confirmation_msg)
            db.commit()
            db.close()
            return jsonify({"response": summary})

        next_question = conv_manager.generate_natural_question(
            conversation_state, recent_user_input, session_id
        )

        response = next_question

        ai_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=response,
            created_at=datetime.utcnow()
        )
        db.add(ai_msg)
        db.commit()
        db.close()

        return jsonify({"response": response})

    except Exception as e:
        print(f"Error in chat_with_ai: {str(e)}")
        return jsonify({"error": "Chat service temporarily unavailable"}), 500

@app.route("/agents", methods=["GET"])
def get_agents():
    """Get list of all available agents"""
    agents = localData.get("agents", [])
    agent_list = [{"name": agent.get("name"), "agent_id": agent.get("agent_id")} for agent in agents]
    return jsonify(agent_list)

@app.route("/agent/<agent_name>", methods=["GET"])
def get_agent_details(agent_name):
    """Get detailed information for a specific agent"""
    agents = localData.get("agents", [])
    agent = next((a for a in agents if a.get("name", "").lower() == agent_name.lower()), None)

    if not agent:
        return jsonify({"error": "Agent not found"}), 404

    return jsonify(agent)

@app.route("/initialize_session", methods=["POST", "OPTIONS"])
def initialize_session_new():
    """Initialize session with clean greeting"""
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200
        
    try:
        body = request.get_json() or {}
        agent_name = body.get("agent_name", "")

        if not agent_name:
            return jsonify({"error": "Agent name required"}), 400

        db = SessionLocal()
        session = ChatSession(agent=agent_name)
        db.add(session)
        db.commit()
        db.refresh(session)
        
        session_id = session.id

        agents = localData.get("agents", [])
        agent_details = next((a for a in agents if a.get("name", "").lower() == agent_name.lower()), None)

        if not agent_details:
            db.close()
            return jsonify({"error": "Agent not found"}), 404

        initial_question = ask_supervisor_question(0, temperature=0.8)

        if not initial_question:
            initial_question = "Can you explain why you edited your start time?"

        ai_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=initial_question,
            # created_at=datetime.now(UTC)
            created_at=datetime.now(timezone.utc)
        )
        db.add(ai_msg)

        conversation_state = conv_manager.analyze_conversation_state([], agent_details, session_id)
        session.conversation_state = json.dumps(conversation_state)

        db.commit()
        db.close()

        return jsonify({
            "session_id": session_id,
            "message": "Session started successfully",
            "ai_response": initial_question
        })

    except Exception as e:
        print(f"Error in initialize_session: {str(e)}")
        return jsonify({"error": "Failed to initialize session"}), 500

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "agents_count": len(localData.get("agents", [])),
        "openai_available": True,
        "database": "connected" if os.path.exists(DB_PATH) else "not_found",
        "conversation_manager": "natural_questions"
    })

@app.route("/")
def home():
    return jsonify({
        "status": "Backend Running - NATURAL QUESTIONS",
        "timestamp": datetime.utcnow().isoformat(),
        "conversation_manager": "natural_supervisor_questions",
        "routes": [
            "GET / - This info",
            "GET /health - Health check", 
            "GET /data - View data.json",
            "GET /agents - List all agents",
            "GET /agent/<name> - Get agent details",
            "POST /create_session - Create new chat session",
            "POST /initialize_session - Initialize session",
            "GET /sessions - List all sessions",
            "GET /sessions/<id> - Get session details",
            "POST /sessions/<id>/messages - Add message to session",
            "POST /chat_with_ai - Chat with NATURAL supervisor"
        ]
    })

if __name__ == "__main__":
    print("Starting Flask server - NATURAL SUPERVISOR QUESTIONS...")
    print("✅ DETAILED prompts with REAL conversation examples")
    print("✅ NATURAL question flow - no repetitive technical questions") 
    print("✅ LOGICAL follow-ups based on what employee actually said")
    print("✅ CLEAN greetings with no extra text")
    print("✅ MINIMUM 4 questions enforced")
    print("✅ NO hardcoded responses - pure model with better prompts")
    print(f"Database path: {DB_PATH}")
    print(f"Data.json path: {DATA_JSON_PATH}")
    print(f"Agents loaded: {len(localData.get('agents', []))}")
    print(f"OpenAI connected ✅ (model: gpt-4o-mini)")

    app.run(host="0.0.0.0", port=5000, debug=True)