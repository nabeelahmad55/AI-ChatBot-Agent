import express from "express";
import dotenv from "dotenv";
import OpenAI from "openai";
import cors from "cors";

dotenv.config();
const app = express();
app.use(express.json());
app.use(cors());
app.use(express.static("public"));

const openai = new OpenAI({
  // apiKey: process.env.OPENAI_API_KEY,
  baseURL: "http://localhost:11434/v1",
  apiKey: "ollama",
});

app.post("/chat", async (req, res) => {
  const { pageContent, userMessage } = req.body;

  const prompt = `
You are an AI assistant who is the **owner and developer** of this website. 
You know all the details about its components, sections, and functionality.

Webpage content:
---
${pageContent}
---

Instructions:
1. If this is the first interaction (userMessage is empty):
   - Greet the visitor **once**.
   - Ask an engaging, context-aware question about the page content.
2. If the visitor asks a question (userMessage is not empty):
   - Answer the question **directly and concisely**.
   - Do **not repeat greetings** or say "Hello".
   - Provide relevant details about the page content, features, or components.
3. Avoid generic, repetitive, or filler sentences.
4. Always stay **owner-aware** and knowledgeable about the page.

Visitor message:
"${userMessage || ""}"
`;

  try {
    const completion = await openai.chat.completions.create({
      model: "qwen:1.8b",   
      // phi3:latest
      messages: [{ role: "user", content: prompt }],
    });

    const reply = completion.choices[0].message.content;
    res.json({ answer: reply });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "AI Error" });
  }
});

app.listen(process.env.PORT, () => {
  console.log(`Server running → http://localhost:${process.env.PORT}`);
});

app.get("/", (req, res) => {
  res.send("✅ Server is running — backend working fine!");
});
