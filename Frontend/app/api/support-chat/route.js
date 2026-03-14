import { consumeStream, convertToModelMessages, streamText } from "ai"

export const maxDuration = 30

export async function POST(req) {
  const { messages } = await req.json()

  const result = streamText({
    model: "openai/gpt-5-mini",
    prompt: convertToModelMessages(messages),
    abortSignal: req.signal,
  })

  return result.toUIMessageStreamResponse({
    consumeSseStream: consumeStream,
  })
}
