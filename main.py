import openai
import os
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
import json

"""
Before submitting the assignment, describe here in a few sentences what you would have built next if you spent 2 more hours on this project:

If I had 2 more hours, I would have implemented:
1. Story categorization system - classify requests (adventure, fairy tale, educational, etc.) and use tailored generation strategies for each category
2. Interactive story elements - allow users to make choices during the story that affect the outcome, creating a "choose your own adventure" experience
3. Story persistence - save generated stories to files with metadata (user request, generation timestamp, ratings) for future reference
4. Enhanced feedback loop - allow users to rate stories and request specific modifications ("make it funnier", "add more animals", etc.)
5. Character consistency tracking - maintain character details across longer stories or story series
6. Illustration prompts - generate descriptions that could be used to create accompanying images for the stories

UPDATE: Now implemented Genre-aware prompting, Stateful memory system, and Feedback loop for story revision!
"""

@dataclass
class Character:
    """Represents a character in the story universe"""
    name: str
    description: str
    personality: List[str]
    relationships: Dict[str, str] = field(default_factory=dict)

@dataclass
class StoryMemory:
    """Maintains state across story sessions"""
    current_story: str = ""
    genre: str = ""
    characters: Dict[str, Character] = field(default_factory=dict)
    world_details: Dict[str, str] = field(default_factory=dict)
    story_history: List[Dict[str, Any]] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    
    def add_story(self, story: str, genre: str, user_request: str, quality_score: int = 0):
        """Add a story to the history"""
        self.story_history.append({
            "story": story,
            "genre": genre,
            "request": user_request,
            "quality_score": quality_score,
            "characters": list(self.characters.keys())
        })
        self.current_story = story
        self.genre = genre

class GenrePromptEngine:
    """Handles genre-specific prompt engineering"""
    
    GENRE_TEMPLATES = {
        "adventure": {
            "elements": ["brave protagonist", "exciting quest", "obstacles to overcome", "discovery"],
            "tone": "exciting and energetic",
            "structure": "journey with challenges and triumph",
            "vocabulary": "action words, vivid descriptions of places and events"
        },
        "fairy_tale": {
            "elements": ["magical elements", "clear good vs evil", "transformation", "happy ending"],
            "tone": "whimsical and magical",
            "structure": "once upon a time format with magical resolution",
            "vocabulary": "magical, enchanted, sparkling, mysterious"
        },
        "educational": {
            "elements": ["learning opportunity", "problem-solving", "factual information", "practical lessons"],
            "tone": "encouraging and informative",
            "structure": "problem-discovery-learning-application",
            "vocabulary": "clear explanations, age-appropriate facts"
        },
        "friendship": {
            "elements": ["character relationships", "cooperation", "empathy", "shared experiences"],
            "tone": "warm and heartfelt",
            "structure": "relationship challenge and resolution",
            "vocabulary": "emotions, caring, helping, understanding"
        },
        "fantasy": {
            "elements": ["magical creatures", "fantastical settings", "special powers", "wonder"],
            "tone": "mysterious and wondrous",
            "structure": "magical world with extraordinary events",
            "vocabulary": "mystical, enchanted, powerful, extraordinary"
        }
    }
    
    @classmethod
    def detect_genre(cls, user_request: str) -> str:
        """Detect the genre from user request"""
        request_lower = user_request.lower()
        
        # Genre detection keywords
        genre_keywords = {
            "adventure": ["adventure", "quest", "journey", "explore", "brave", "hero"],
            "fairy_tale": ["princess", "prince", "magic", "fairy", "castle", "witch", "dragon"],
            "educational": ["learn", "teach", "school", "facts", "science", "math", "educational"],
            "friendship": ["friend", "friendship", "together", "help", "kind", "caring"],
            "fantasy": ["magical", "wizard", "unicorn", "fantasy", "mystical", "enchanted"]
        }
        
        # Score each genre
        genre_scores = {}
        for genre, keywords in genre_keywords.items():
            score = sum(1 for keyword in keywords if keyword in request_lower)
            genre_scores[genre] = score
        
        # Return highest scoring genre, default to adventure
        detected_genre = max(genre_scores, key=genre_scores.get)
        return detected_genre if genre_scores[detected_genre] > 0 else "adventure"
    
    @classmethod
    def get_genre_prompt(cls, genre: str, user_request: str, is_episode: bool = False) -> str:
        """Generate genre-specific prompts"""
        template = cls.GENRE_TEMPLATES.get(genre, cls.GENRE_TEMPLATES["adventure"])
        
        base_prompt = f"""Create an engaging {genre} story for children ages 5-10 based on: '{user_request}'

GENRE-SPECIFIC REQUIREMENTS for {genre.upper()}:
- Include these elements: {', '.join(template['elements'])}
- Maintain a {template['tone']} tone throughout
- Follow this structure: {template['structure']}
- Use {template['vocabulary']} in your language choices

GENERAL REQUIREMENTS:
- Be appropriate for children ages 5-10 (no scary or inappropriate content)
- Be approximately 200-400 words long
- Include descriptive language and dialogue
- Teach a gentle lesson or moral
- Have a clear beginning, middle, and satisfying end"""

        if is_episode:
            base_prompt += f"\n- This is a continuation episode, maintain consistency with established {genre} elements from previous story"
        
        return base_prompt + "\n\nPlease write the complete story now:"

def call_model(prompt: str, max_tokens=3000, temperature=0.1) -> Optional[str]:
    """
    Call OpenAI API with error handling
    """
    try:
        # Get API key from environment variable
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("❌ Error: OPENAI_API_KEY environment variable not set!")
            print("Please set your OpenAI API key as an environment variable:")
            print("  export OPENAI_API_KEY='your-api-key-here'")
            print("Or on Windows:")
            print("  set OPENAI_API_KEY=your-api-key-here")
            return None
        
        openai.api_key = api_key
        
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            stream=False,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp.choices[0].message["content"]
    except Exception as e:
        print(f"❌ Error calling OpenAI API: {e}")
        print("Please check your API key and internet connection.")
        return None

example_requests = [
    "A story about a girl named Alice and her best friend Bob, who happens to be a cat. They go on a magical adventure in their backyard.",
    "A brave little mouse who wants to become a knight",
    "Two siblings who discover a secret door in their grandmother's attic",
    "A friendly dragon who is afraid of flying",
    "A young inventor who creates a robot companion"
]

def extract_characters(story: str, memory: StoryMemory) -> None:
    """Extract and store character information from the story"""
    extract_prompt = f"""Analyze this story and extract the main characters with their details:

{story}

For each main character, provide:
- Name
- Brief description (appearance, role)
- 2-3 personality traits
- Relationships to other characters

Format as: CHARACTER_NAME: description | personality: trait1, trait2, trait3 | relationships: name-relationship

Example: Alice: young girl with curly hair, main protagonist | personality: curious, brave, kind | relationships: Bob-best friend"""
    
    result = call_model(extract_prompt, max_tokens=500)
    if result:
        # Parse and store characters (simplified parsing)
        lines = result.split('\n')
        for line in lines:
            if ':' in line and '|' in line:
                try:
                    parts = line.split('|')
                    name_desc = parts[0].split(':')
                    if len(name_desc) >= 2:
                        name = name_desc[0].strip()
                        description = name_desc[1].strip()
                        
                        # Extract personality traits
                        personality = []
                        for part in parts:
                            if 'personality:' in part.lower():
                                traits = part.split(':')[1].strip().split(',')
                                personality = [t.strip() for t in traits]
                        
                        memory.characters[name] = Character(
                            name=name,
                            description=description,
                            personality=personality
                        )
                except:
                    continue  # Skip malformed lines

def get_user_feedback() -> Dict[str, Any]:
    """Get user feedback on the story"""
    print("\n📝 Quick feedback (optional):")
    print("Rate the story (1-5, or press Enter to skip):", end=" ")
    
    rating_input = input().strip()
    rating = 0
    if rating_input.isdigit() and 1 <= int(rating_input) <= 5:
        rating = int(rating_input)
    
    feedback = ""
    if rating > 0:
        if rating <= 2:
            print("What could make it better?", end=" ")
            feedback = input().strip()
        elif rating >= 4:
            print("What did you like most?", end=" ")
            feedback = input().strip()
    
    return {"rating": rating, "feedback": feedback}

def revise_story_with_feedback(story: str, feedback: Dict[str, Any], user_request: str) -> Optional[str]:
    """Revise story based on user feedback"""
    if not feedback.get("feedback") or feedback.get("rating", 0) >= 4:
        return story  # No revision needed
    
    revision_prompt = f"""The user provided this feedback about the story: "{feedback['feedback']}"
They rated it {feedback['rating']}/5.

Original request: {user_request}
Current story:
{story}

Please revise the story to address their feedback while maintaining the core story elements. Make specific improvements based on their comments.

IMPORTANT: Provide ONLY the revised story text, no explanations."""
    
    revised = call_model(revision_prompt)
    return revised if revised else story

def generate_story(user_input: str, memory: StoryMemory, is_episode: bool = False) -> Optional[str]:
    """
    Generate a story using genre-aware prompting and stateful memory
    """
    print("📝 Creating your story...")
    
    # Detect genre for new stories
    if not is_episode:
        memory.genre = GenrePromptEngine.detect_genre(user_input)
        print(f"🎭 Detected genre: {memory.genre.replace('_', ' ').title()}")
    
    # Create genre-aware prompt
    if is_episode and memory.current_story:
        # Include character information for episodes
        character_info = ""
        if memory.characters:
            char_list = []
            for char in memory.characters.values():
                char_details = f"{char.name}: {char.description}"
                if char.personality:
                    char_details += f" (personality: {', '.join(char.personality)})"
                char_list.append(char_details)
            character_info = f"\n\nESTABLISHED CHARACTERS:\n" + "\n".join(char_list)
        
        storyteller_prompt = f"""{GenrePromptEngine.get_genre_prompt(memory.genre, user_input, True)}

PREVIOUS STORY CONTEXT:
{memory.current_story[-500:]}...{character_info}

Continue the adventure with these established characters and world."""
    else:
        storyteller_prompt = GenrePromptEngine.get_genre_prompt(memory.genre, user_input, False)
    
    # Generate initial story
    initial_story = call_model(storyteller_prompt)
    if not initial_story:
        return None
    
    print("🔍 Evaluating story quality...")
    
    # Judge with genre-specific criteria
    judge_prompt = f"""Evaluate this {memory.genre} story for children ages 5-10:

{initial_story}

Focus on:
1. Genre adherence (does it feel like a good {memory.genre} story?)
2. Age-appropriateness and engagement
3. Character development and consistency
4. Story structure and pacing
5. Educational value and positive messages

Provide specific suggestions for improvement. Rate overall quality 1-5."""
    
    evaluation = call_model(judge_prompt, max_tokens=1000)
    if not evaluation:
        return initial_story
    
    print("✨ Refining the story...")
    
    # Refine with genre awareness
    refine_prompt = f"""Based on this evaluation for a {memory.genre} story:

{evaluation}

Improve this story while maintaining its {memory.genre} elements:

{initial_story}

IMPORTANT: Provide ONLY the improved story text."""
    
    final_story = call_model(refine_prompt)
    story = final_story if final_story else initial_story
    
    # Extract characters for memory
    if not is_episode:
        extract_characters(story, memory)
    
    return story

def display_welcome():
    """Display welcome message and instructions"""
    print("🌟 Welcome to the Children's Story Generator! 🌟")
    print("I can create fun, engaging stories for kids ages 5-10.")
    print("\nExample requests:")
    print("  • A story about a girl named Alice and her best friend Bob, who happens to be a cat")
    print("  • A brave little mouse who wants to become a knight") 
    print("  • Two siblings who discover a secret door in their grandmother's attic")
    print("  • A friendly dragon who is afraid of flying")
    print()

def assess_story_quality(story: str, memory: StoryMemory) -> bool:
    """
    Assess if a story is good enough to offer episode continuation
    """
    assessment_prompt = f"""Assess this {memory.genre} story for episode potential:

{story}

Consider:
- Character development and likability for {memory.genre} stories
- World-building potential in the {memory.genre} genre
- Story engagement level
- Whether characters/setting could support more {memory.genre} adventures

Respond with only "YES" if this has good episode potential, or "NO" if it doesn't."""
    
    result = call_model(assessment_prompt, max_tokens=100, temperature=0.1)
    return result and "YES" in result.upper()

def get_user_choice(memory: StoryMemory) -> str:
    """
    Get user's choice for what to do next with genre context
    """
    print(f"\n🌟 What would you like to do next? (Current genre: {memory.genre.replace('_', ' ').title()})")
    print(f"  1. Continue with a {memory.genre.replace('_', ' ')} episode featuring the same characters")
    print("  2. Create a completely new story")
    print("  3. Quit")
    
    while True:
        choice = input("Enter your choice (1, 2, or 3): ").strip()
        if choice in ['1', '2', '3']:
            return choice
        print("Please enter 1, 2, or 3.")

def main():
    """Main application loop with enhanced memory and feedback"""
    display_welcome()
    
    # Check if API key is available before starting
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OpenAI API key not found!")
        print("\nTo use this application, you need to set your OpenAI API key:")
        print("\n🔧 Setup Instructions:")
        print("1. Get your API key from: https://platform.openai.com/api-keys")
        print("2. Set it as an environment variable:")
        print("   • On Mac/Linux: export OPENAI_API_KEY='your-key-here'")
        print("   • On Windows: set OPENAI_API_KEY=your-key-here")
        print("3. Restart the application")
        print("\n💡 Tip: You can also add it to your .bashrc/.zshrc for persistence")
        return
    
    # Initialize stateful memory
    memory = StoryMemory()
    story_count = 0
    
    while True:
        # Determine input based on state
        if story_count == 0:
            user_input = input("What kind of story would you like to hear? (or 'quit' to exit): ").strip()
            is_episode = False
        else:
            # Check if previous story is good enough for episodes
            if assess_story_quality(memory.current_story, memory):
                choice = get_user_choice(memory)
                
                if choice == '1':  # Episode
                    user_input = input(f"\nWhat should happen in the next {memory.genre.replace('_', ' ')} episode? ").strip()
                    is_episode = True
                elif choice == '2':  # New story
                    user_input = input("\nWhat kind of new story would you like to hear? ").strip()
                    is_episode = False
                    # Reset character memory for new story
                    memory.characters.clear()
                else:  # Quit
                    break
            else:
                # Story wasn't engaging enough for episodes
                user_input = input("\nWhat kind of story would you like to hear next? (or 'quit' to exit): ").strip()
                is_episode = False
                memory.characters.clear()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            break
        
        if not user_input:
            print("Please tell me what kind of story you'd like!")
            continue
            
        print()  # Add spacing
        story = generate_story(user_input, memory, is_episode)
        
        if story:
            episode_text = "episode" if is_episode else "story"
            print(f"🎉 Here's your {episode_text}:\n")
            print("─" * 50)
            print(story)
            print("─" * 50)
            
            # Get user feedback
            feedback = get_user_feedback()
            
            # Revise if needed
            if feedback.get("rating", 0) <= 2 and feedback.get("feedback"):
                print("\n🔄 Let me improve that for you...")
                revised_story = revise_story_with_feedback(story, feedback, user_input)
                if revised_story != story:
                    print("✨ Here's the improved version:\n")
                    print("─" * 50)
                    print(revised_story)
                    print("─" * 50)
                    story = revised_story
            
            # Store in memory
            memory.add_story(story, memory.genre, user_input, feedback.get("rating", 0))
            story_count += 1
            
            # Update user preferences based on feedback
            if feedback.get("rating", 0) >= 4:
                genre_pref = memory.user_preferences.get("preferred_genres", {})
                genre_pref[memory.genre] = genre_pref.get(memory.genre, 0) + 1
                memory.user_preferences["preferred_genres"] = genre_pref
                
        else:
            episode_text = "episode" if is_episode else "story"
            print(f"Sorry, I had trouble creating your {episode_text}. Please try again!")
        
        print()  # Add spacing before next prompt
    
    # Goodbye message with personalization
    if story_count > 0:
        stories_text = "story" if story_count == 1 else "stories"
        print(f"\nThanks for listening to {story_count} {stories_text}! 📚")
        
        # Show favorite genre if available
        if memory.user_preferences.get("preferred_genres"):
            fav_genre = max(memory.user_preferences["preferred_genres"], key=memory.user_preferences["preferred_genres"].get)
            print(f"I noticed you really enjoyed {fav_genre.replace('_', ' ')} stories! 🌟")
    
    print("Sweet dreams! Goodbye! 🌙")

if __name__ == "__main__":
    main()