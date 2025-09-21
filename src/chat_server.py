"""Chat server implementation with Llama model and multi-chat support."""

import os
import sqlite3
import threading
import time
import uuid
import json
import re
from datetime import datetime
from pathlib import Path
from llama_cpp import Llama

from config import LLAMA3_MODEL


class Llama3MultiChatServer:
    def __init__(self):
        self.model = None
        self.chat_sessions = {}
        self.max_context_pairs = 10
        self.max_context_tokens = 6000

        # Make database path relative to this script
        script_dir = Path(__file__).parent
        data_dir = script_dir / "../data"
        data_dir.mkdir(exist_ok=True)
        self.memory_db = data_dir / "llama3_multichat_memory.db"
        self.model_busy = False
        self.model_lock = threading.Lock()

        self.init_database()
        self.load_model()

    def load_model(self):
        """Load the Llama 3 model"""
        model_path = LLAMA3_MODEL["path"]

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")

        print(f"🚀 Loading {LLAMA3_MODEL['name']}...")
        print(f"📍 {os.path.basename(model_path)}")

        start_time = time.time()
        self.model = Llama(
            model_path=model_path,
            n_ctx=LLAMA3_MODEL["n_ctx"],
            n_gpu_layers=LLAMA3_MODEL["n_gpu_layers"],
            verbose=False,
            seed=-1
        )

        load_time = time.time() - start_time
        print(f"✅ Model loaded in {load_time:.1f}s")

    def init_database(self):
        """Initialize SQLite database for multi-chat support"""
        try:
            conn = sqlite3.connect(self.memory_db)
            cursor = conn.cursor()

            # Create chats table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chats (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create messages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tokens INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (chat_id) REFERENCES chats (id) ON DELETE CASCADE
                )
            ''')

            # Create facts table (per chat)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (chat_id) REFERENCES chats (id) ON DELETE CASCADE,
                    UNIQUE(chat_id, key)
                )
            ''')

            # Create preferences table (per chat)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    category TEXT,
                    item TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (chat_id) REFERENCES chats (id) ON DELETE CASCADE
                )
            ''')

            # Create experiences table (per chat)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS experiences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    experience TEXT,
                    context TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (chat_id) REFERENCES chats (id) ON DELETE CASCADE
                )
            ''')

            # Create topics table (per chat)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (chat_id) REFERENCES chats (id) ON DELETE CASCADE,
                    UNIQUE(chat_id, topic)
                )
            ''')

            conn.commit()
            conn.close()
            print("✅ Multi-chat database initialized")

        except Exception as e:
            print(f"⚠️ Database init error: {e}")

    def create_chat(self, first_message):
        """Create a new chat and generate title"""
        chat_id = str(uuid.uuid4())
        title = self.generate_chat_title(first_message)

        try:
            conn = sqlite3.connect(self.memory_db)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO chats (id, title) VALUES (?, ?)
            ''', (chat_id, title))

            conn.commit()
            conn.close()

            # Initialize empty conversation history
            self.chat_sessions[chat_id] = []
            return chat_id, title

        except Exception as e:
            print(f"⚠️ Error creating chat: {e}")
            return None, None

    def generate_chat_title(self, first_message):
        """Generate a short title for the chat based on the first message"""
        try:
            title_prompt = f"<|start_header_id|>user<|end_header_id|>\n\nCreate a very short (2-4 words) title for a chat that starts with: '{first_message[:100]}'\n\nTitle:<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"

            result = self.model(
                title_prompt,
                max_tokens=20,
                temperature=0.3,
                stop=["<|eot_id|>", "\n"]
            )

            title = result['choices'][0]['text'].strip()
            title = re.sub(r'^["\']|["\']$', '', title)
            title = title.replace('\n', ' ').strip()

            if not title or len(title) > 50:
                words = first_message.split()[:3]
                title = ' '.join(words).capitalize()

            return title if title else "New Chat"

        except Exception as e:
            print(f"⚠️ Title generation error: {e}")
            words = first_message.split()[:3]
            return ' '.join(words).capitalize() if words else "New Chat"

    def get_chats(self):
        """Get list of all chats"""
        try:
            conn = sqlite3.connect(self.memory_db)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, title, created_at, updated_at
                FROM chats
                ORDER BY updated_at DESC
            ''')

            chats = cursor.fetchall()
            conn.close()

            return [
                {
                    "id": chat[0],
                    "title": chat[1],
                    "created_at": chat[2],
                    "updated_at": chat[3]
                }
                for chat in chats
            ]

        except Exception as e:
            print(f"⚠️ Error getting chats: {e}")
            return []

    def get_chat_messages(self, chat_id):
        """Get messages for a specific chat"""
        try:
            conn = sqlite3.connect(self.memory_db)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT role, content, created_at
                FROM messages
                WHERE chat_id = ?
                ORDER BY created_at ASC
            ''', (chat_id,))

            messages = cursor.fetchall()
            conn.close()

            return [
                {
                    "role": msg[0],
                    "content": msg[1],
                    "created_at": msg[2]
                }
                for msg in messages
            ]

        except Exception as e:
            print(f"⚠️ Error getting messages: {e}")
            return []

    def save_message(self, chat_id, role, content, tokens=0):
        """Save a message to the database"""
        try:
            conn = sqlite3.connect(self.memory_db)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO messages (chat_id, role, content, tokens)
                VALUES (?, ?, ?, ?)
            ''', (chat_id, role, content, tokens))

            cursor.execute('''
                UPDATE chats SET updated_at = CURRENT_TIMESTAMP WHERE id = ?
            ''', (chat_id,))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"⚠️ Error saving message: {e}")

    def get_memory_counts(self, chat_id):
        """Get memory counts for a specific chat"""
        try:
            conn = sqlite3.connect(self.memory_db)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM facts WHERE chat_id = ?", (chat_id,))
            facts_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM experiences WHERE chat_id = ?", (chat_id,))
            experiences_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM topics WHERE chat_id = ?", (chat_id,))
            topics_count = cursor.fetchone()[0]

            conn.close()
            return facts_count, experiences_count, topics_count
        except:
            return 0, 0, 0

    def get_relevant_memories(self, chat_id, user_input):
        """Retrieve relevant memories for current context"""
        relevant = []
        user_lower = user_input.lower()

        try:
            conn = sqlite3.connect(self.memory_db)
            cursor = conn.cursor()

            self_queries = ["my name", "who am i", "about me", "remember me", "know about me"]
            if any(query in user_lower for query in self_queries):
                cursor.execute("SELECT key, value FROM facts WHERE chat_id = ?", (chat_id,))
                facts = cursor.fetchall()
                if facts:
                    facts_str = ", ".join([f"{k}: {v}" for k, v in facts])
                    relevant.append(f"Facts about you: {facts_str}")

                cursor.execute("SELECT category, GROUP_CONCAT(item, ', ') FROM preferences WHERE chat_id = ? GROUP BY category", (chat_id,))
                prefs = cursor.fetchall()
                if prefs:
                    for category, items in prefs:
                        relevant.append(f"You {category}: {items}")

            cursor.execute("SELECT topic, frequency FROM topics WHERE chat_id = ? AND topic LIKE ?", (chat_id, f'%{user_lower}%'))
            topics = cursor.fetchall()
            for topic, count in topics:
                if topic in user_lower:
                    relevant.append(f"Previous {topic} discussions: {count} times")

            cursor.execute("SELECT experience FROM experiences WHERE chat_id = ? ORDER BY created_at DESC LIMIT 5", (chat_id,))
            experiences = cursor.fetchall()
            for (experience,) in experiences:
                if any(word in user_lower for word in experience.split()):
                    relevant.append(f"Recent experience: {experience}")

            conn.close()
        except Exception as e:
            print(f"⚠️ Memory retrieval error: {e}")

        return relevant

    def extract_memory_elements(self, chat_id, user_input, assistant_response):
        """Extract facts, preferences, and experiences from conversation"""
        memories_added = 0

        try:
            conn = sqlite3.connect(self.memory_db)
            cursor = conn.cursor()

            fact_patterns = [
                (r"my name is (\w+)", "name"),
                (r"i am (\w+)", "name"),
                (r"call me (\w+)", "name"),
                (r"i am (\d+) years old", "age"),
                (r"i live in ([^,.]+)", "location"),
                (r"i work as a ([^,.]+)", "job"),
                (r"i am a ([^,.]+)", "profession"),
                (r"my job is ([^,.]+)", "job"),
            ]

            for pattern, key in fact_patterns:
                match = re.search(pattern, user_input.lower())
                if match:
                    value = match.group(1).strip()
                    cursor.execute('''
                        INSERT OR REPLACE INTO facts (chat_id, key, value, updated_at)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (chat_id, key, value))
                    memories_added += 1

            preference_patterns = [
                (r"i like ([^,.]+)", "likes"),
                (r"i love ([^,.]+)", "loves"),
                (r"i prefer ([^,.]+)", "prefers"),
                (r"my favorite ([^\s]+) is ([^,.]+)", "favorites"),
                (r"i don't like ([^,.]+)", "dislikes"),
                (r"i hate ([^,.]+)", "hates"),
            ]

            for pattern, category in preference_patterns:
                matches = re.findall(pattern, user_input.lower())
                for match in matches:
                    if category == "favorites":
                        fav_type, fav_item = match
                        fact_key = f"favorite_{fav_type}"
                        cursor.execute('''
                            INSERT OR REPLACE INTO facts (chat_id, key, value, updated_at)
                            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                        ''', (chat_id, fact_key, fav_item))
                    else:
                        item = match if isinstance(match, str) else match[0]
                        cursor.execute('''
                            INSERT INTO preferences (chat_id, category, item)
                            VALUES (?, ?, ?)
                        ''', (chat_id, category, item))
                    memories_added += 1

            experience_patterns = [
                r"i (went to|visited|traveled to) ([^,.]+)",
                r"i (learned|studied) ([^,.]+)",
                r"i (bought|purchased) ([^,.]+)",
                r"i (finished|completed) ([^,.]+)",
                r"i (started) ([^,.]+)",
            ]

            for pattern in experience_patterns:
                matches = re.findall(pattern, user_input.lower())
                for match in matches:
                    action, object_item = match
                    experience = f"{action} {object_item}"
                    cursor.execute('''
                        INSERT INTO experiences (chat_id, experience, context)
                        VALUES (?, ?, ?)
                    ''', (chat_id, experience, user_input[:100]))
                    memories_added += 1

            topics = re.findall(r'\b(programming|python|javascript|machine learning|ai|artificial intelligence|data science|web development|coding|software)\b', user_input.lower())
            for topic in topics:
                cursor.execute('''
                    INSERT INTO topics (chat_id, topic, frequency, updated_at)
                    VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                    ON CONFLICT(chat_id, topic) DO UPDATE SET
                        frequency = frequency + 1,
                        updated_at = CURRENT_TIMESTAMP
                ''', (chat_id, topic))
                memories_added += 1

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"⚠️ Memory extraction error: {e}")

        return memories_added

    def estimate_tokens(self, text):
        """Rough token estimation"""
        return len(text) // 4

    def build_context_with_memory(self, chat_id, user_input):
        """Build prompt with conversation context + episodic memory"""
        relevant_memories = self.get_relevant_memories(chat_id, user_input)

        memory_context = ""
        if relevant_memories:
            memory_context = "\n[Memory Context: " + "; ".join(relevant_memories) + "]\n"

        db_messages = self.get_chat_messages(chat_id)

        conversation_history = []
        current_pair = {}

        for msg in db_messages:
            if msg['role'] == 'user':
                if current_pair:
                    conversation_history.append(current_pair)
                current_pair = {'user': msg['content']}
            elif msg['role'] == 'assistant' and 'user' in current_pair:
                current_pair['assistant'] = msg['content']

        if 'user' in current_pair and 'assistant' in current_pair:
            conversation_history.append(current_pair)

        if not conversation_history:
            return f"<|start_header_id|>user<|end_header_id|>\n\n{memory_context}{user_input}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"

        context_parts = []
        for exchange in conversation_history:
            context_parts.append(f"<|start_header_id|>user<|end_header_id|>\n\n{exchange['user']}<|eot_id|>")
            context_parts.append(f"<|start_header_id|>assistant<|end_header_id|>\n\n{exchange['assistant']}<|eot_id|>")

        context_parts.append(f"<|start_header_id|>user<|end_header_id|>\n\n{memory_context}{user_input}<|eot_id|>")
        context_parts.append("<|start_header_id|>assistant<|end_header_id|>\n\n")

        return ''.join(context_parts)

    def add_to_conversation(self, chat_id, user_input, assistant_response):
        """Add exchange to conversation with context management"""
        if chat_id not in self.chat_sessions:
            self.chat_sessions[chat_id] = []

        self.chat_sessions[chat_id].append({
            "user": user_input,
            "assistant": assistant_response,
            "tokens": self.estimate_tokens(user_input + assistant_response),
            "timestamp": datetime.now().isoformat()
        })

        if len(self.chat_sessions[chat_id]) > self.max_context_pairs:
            self.chat_sessions[chat_id] = self.chat_sessions[chat_id][-self.max_context_pairs:]

    def generate_response(self, chat_id, user_input, is_first_message=False):
        """Generate response to user input"""
        if not self.model:
            return "Error: Model not loaded", 0

        acquired = self.model_lock.acquire(blocking=False)
        if not acquired:
            return "Error: Model is busy processing another request", 0

        try:
            if is_first_message:
                chat_id, title = self.create_chat(user_input)
                if not chat_id:
                    return "Error: Could not create chat", 0, None, None
            else:
                title = None

            prompt = self.build_context_with_memory(chat_id, user_input)

            result = self.model(
                prompt,
                max_tokens=512,
                temperature=0.7,
                top_p=0.95,
                stop=["<|eot_id|>"]
            )

            response = result['choices'][0]['text'].strip()

            self.add_to_conversation(chat_id, user_input, response)

            user_tokens = self.estimate_tokens(user_input)
            assistant_tokens = self.estimate_tokens(response)

            self.save_message(chat_id, "user", user_input, user_tokens)
            self.save_message(chat_id, "assistant", response, assistant_tokens)

            memories_added = self.extract_memory_elements(chat_id, user_input, response)

            return response, memories_added, chat_id, title

        except Exception as e:
            print(f"❌ Generation error: {e}")
            return f"Sorry, error occurred: {str(e)}", 0, None, None

        finally:
            self.model_lock.release()

    def generate_streaming_response(self, chat_id, user_input, output_stream):
        """Generate streaming response to user input"""
        if not self.model:
            return "Error: Model not loaded", 0

        acquired = self.model_lock.acquire(blocking=False)
        if not acquired:
            return "Error: Model is busy processing another request", 0

        try:
            # Save user message immediately
            user_tokens = self.estimate_tokens(user_input)
            self.save_message(chat_id, "user", user_input, user_tokens)

            prompt = self.build_context_with_memory(chat_id, user_input)

            stream_response = self.model(
                prompt,
                max_tokens=512,
                temperature=0.7,
                top_p=0.95,
                stop=["<|eot_id|>"],
                stream=True
            )

            response_parts = []
            client_connected = True

            # Continue generation regardless of client connection
            for chunk in stream_response:
                if isinstance(chunk, dict):
                    token = None

                    if 'choices' in chunk and len(chunk['choices']) > 0:
                        choice = chunk['choices'][0]

                        if 'delta' in choice and isinstance(choice['delta'], dict):
                            if 'content' in choice['delta'] and choice['delta']['content']:
                                token = choice['delta']['content']
                        elif 'text' in choice and choice['text']:
                            token = choice['text']

                    elif 'text' in chunk and chunk['text']:
                        token = chunk['text']

                    if token:
                        response_parts.append(token)

                        # Try to send to client, but don't stop generation if disconnected
                        if client_connected:
                            token_data = {'token': token}
                            try:
                                output_stream.write(f"data: {json.dumps(token_data)}\n\n".encode())
                                output_stream.flush()
                            except (BrokenPipeError, ConnectionResetError):
                                print("Client disconnected - continuing generation in background")
                                client_connected = False

            # Complete response generated, save to database
            response = ''.join(response_parts)

            if response:
                self.add_to_conversation(chat_id, user_input, response)
                assistant_tokens = self.estimate_tokens(response)
                self.save_message(chat_id, "assistant", response, assistant_tokens)
                memories_added = self.extract_memory_elements(chat_id, user_input, response)
            else:
                memories_added = 0

            return response, memories_added

        except Exception as e:
            print(f"❌ Streaming generation error: {e}")
            return f"Sorry, error occurred: {str(e)}", 0

        finally:
            self.model_lock.release()

    def delete_chat(self, chat_id):
        """Delete a chat and all its data"""
        try:
            conn = sqlite3.connect(self.memory_db)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
            conn.commit()
            conn.close()

            if chat_id in self.chat_sessions:
                del self.chat_sessions[chat_id]

            return True
        except Exception as e:
            print(f"⚠️ Error deleting chat: {e}")
            return False

    def shutdown(self):
        """Graceful shutdown of chat server"""
        print("🔄 Chat server shutting down...")

        # Wait for any ongoing model operations
        if hasattr(self, 'model_lock') and self.model_lock:
            print("⏳ Waiting for model operations to complete...")
            with self.model_lock:
                print("✅ Model operations completed")

        # Clear in-memory sessions
        self.chat_sessions.clear()

        # Model cleanup (if needed)
        if hasattr(self, 'model') and self.model:
            print("🧹 Cleaning up model resources...")
            # The llama-cpp-python model doesn't need explicit cleanup
            # but we can set it to None to help garbage collection
            self.model = None

        print("✅ Chat server shutdown complete")