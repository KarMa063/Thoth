import torch
from typing import List, Dict

class PromptBuilder:
    def build_messages(self, task: str, user_text: str, author: str, style_lines: str, lang: str) -> List[Dict[str, str]]:
        if task == "rewrite":
            if lang == "en":
                sys = "You are a strict rewriting assistant that never hallucinates."
                user = (
                    f"Rewrite the following text in the writing style of {author}.\n"
                    f"CRITICAL RULES:\n"
                    f"1. Preserve the original meaning exactly.\n"
                    f"2. Keep all ORIGINAL names exactly as they are spelled in the input.\n"
                    f"3. Do NOT add any new characters, dialogue, or events not present in the input.\n"
                    f"4. The 'Style samples' below are ONLY for tone. DO NOT use any names or specific events from the style samples.\n"
                    f"5. Output ONLY the rewritten text, starting immediately.\n\n"
                    f"Style samples for tone ONLY:\n{style_lines}\n\n"
                    f"Text to rewrite:\n{user_text}"
                )
            else:
                sys = (
                    "You are a strict rewriting assistant. "
                    "You MUST respond fully in Nepali (Devanagari). "
                    "Do NOT output English. Output ONLY the rewritten text."
                )
                user = (
                    f"{author} को लेखनशैलीमा तलको पाठ पुनर्लेखन गर।\n"
                    f"कडा नियमहरू:\n"
                    f"१. मूल अर्थ उस्तै राख।\n"
                    f"२. दिइएको पाठका नामहरूलाई जस्ताको तस्तै राख।\n"
                    f"३. पाठमा नभएका नयाँ पात्र, संवाद वा घटना नथप।\n"
                    f"४. तलको 'शैली नमुना' केवल भाषा र टोनको लागि हो। नमुनामा भएका कुनै पनि नाम वा विषयवस्तु प्रयोग नगर।\n"
                    f"५. केवल पुनर्लेखित पाठ मात्र देऊ।\n\n"
                    f"शैली नमुना (टोनको लागि मात्र):\n{style_lines}\n\n"
                    f"पुनर्लेखन गर्नुपर्ने पाठ:\n{user_text}"
                )
        elif task == "continue":
            if lang == "en":
                sys = "You are a careful writing assistant."
                user = (
                    f"Continue the text in the writing style of {author}.\n"
                    f"Hard constraints:\n"
                    f"- Continue naturally from the last sentence.\n"
                    f"- Do NOT add unrelated facts.\n"
                    f"- Keep tense and viewpoint consistent.\n"
                    f"- Output ONLY the continuation (no headings/explanations).\n\n"
                    f"Style samples:\n{style_lines}\n\n"
                    f"Text to continue:\n{user_text}"
                )
            else:
                sys = (
                    "You are a careful writing assistant. "
                    "You MUST respond fully in Nepali (Devanagari). "
                    "Do NOT output English. Output ONLY the continuation."
                )
                user = (
                    f"{author} को लेखनशैलीमा तलको पाठलाई अगाडि बढाऊ।\n"
                    f"कडा नियमहरू:\n"
                    f"- अन्तिम वाक्यबाट स्वाभाविक रूपमा निरन्तरता देऊ।\n"
                    f"- असम्बन्धित नयाँ तथ्य नथप।\n"
                    f"- काल/दृष्टिकोण उस्तै राख।\n"
                    f"- केवल निरन्तरता मात्र देऊ (शीर्षक/व्याख्या होइन)।\n\n"
                    f"शैली नमुना:\n{style_lines}\n\n"
                    f"अगाडि बढाउनुपर्ने पाठ:\n{user_text}"
                )
        else:
            raise ValueError(f"Unknown task: {task}")

        return [{"role": "system", "content": sys}, {"role": "user", "content": user}]

    def apply_chat_template(self, tok, messages: List[Dict[str, str]]) -> Dict[str, torch.Tensor]:
        if hasattr(tok, "apply_chat_template"):
            text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        else:
            sys = messages[0]["content"]
            user = messages[1]["content"]
            text = f"System: {sys}\nUser: {user}\nAssistant:"
        return tok(text, return_tensors="pt", padding=True, truncation=True)
