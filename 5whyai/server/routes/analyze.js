import { Router } from 'express'
import OpenAI from 'openai'

const router = Router()

const SYSTEM_PROMPT = `You are a professional root cause analysis assistant using the 5 Whys method. 
Your role is to guide users through structured problem analysis.

Rules:
- Ask short, direct, bold questions (max 10 words)
- Generate exactly 5 realistic possible answers as short button labels (3-8 words each)
- Focus on: process, system, communication, training, control, and follow-up causes
- Do NOT blame people directly — focus on systemic, process, and structural causes
- Root cause categories: Process failure, Communication failure, Training gap, Tool/resource issue, Human error, Management issue, Planning issue, Documentation issue, Quality control issue, Follow-up failure, System weakness
- After 5 Whys, generate a short conclusion and optional full conclusion with corrective and preventive actions

Response must be valid JSON only — no markdown, no extra text.`

function getFallbackAnswers(whyLevel, context) {
  const fallbacks = [
    [
      'Process was not followed',
      'Communication was unclear',
      'There was not enough time',
      'Tools or resources were missing',
      'Responsibility was not defined'
    ],
    [
      'No clear owner assigned',
      'Training was insufficient',
      'Process was not documented',
      'Wrong information was used',
      'No follow-up system existed'
    ],
    [
      'Standards were not enforced',
      'Review step was skipped',
      'Approval was not required',
      'Escalation path was unclear',
      'Workload was too high'
    ],
    [
      'Management did not prioritize it',
      'No measurement system existed',
      'Feedback was not collected',
      'Lessons were not shared',
      'No corrective action was taken'
    ],
    [
      'Root cause was never addressed',
      'Same issue repeated before',
      'No preventive controls existed',
      'Risk was not assessed',
      'Process improvement was ignored'
    ]
  ]
  return fallbacks[Math.min(whyLevel - 1, 4)]
}

function getFallbackQuestion(whyLevel, previousAnswer) {
  const questions = [
    'Why did this problem happen?',
    'Why did this occur?',
    'Why was this allowed to happen?',
    'Why was there no control in place?',
    'Why was this not prevented earlier?'
  ]
  return questions[Math.min(whyLevel - 1, 4)]
}

function getFallbackConclusion(problem, whyPath) {
  const rootCause = whyPath[whyPath.length - 1]?.answer || 'unknown cause'
  return {
    short: `The problem likely stems from a systemic gap rather than a single event. The root cause appears to be "${rootCause}". Addressing the underlying process or control weakness is the highest-priority first step.`,
    rootCauseCategory: 'Process failure',
    problemSummary: problem,
    whyPath: whyPath,
    mostLikelyRootCause: rootCause,
    contributingFactors: [
      'Lack of clear process ownership',
      'Insufficient monitoring or review mechanisms',
      'Communication gaps between responsible parties',
      'Absence of documented standards or controls'
    ],
    correctiveActions: [
      'Immediately assign clear ownership for the affected process',
      'Document the process step-by-step with responsible parties named',
      'Implement a review checkpoint at the point of failure',
      'Brief all relevant team members on the new standard'
    ],
    preventiveActions: [
      'Establish regular process audits to detect early deviations',
      'Create a feedback loop so issues are surfaced quickly',
      'Add the failure mode to risk registers and control plans',
      'Train new and existing staff on the updated process'
    ],
    actionPlan: [
      { priority: 1, action: 'Assign process owner', timeframe: 'Immediate (1–3 days)' },
      { priority: 2, action: 'Document and communicate updated process', timeframe: 'Short-term (1–2 weeks)' },
      { priority: 3, action: 'Implement monitoring checkpoint', timeframe: 'Short-term (2–4 weeks)' },
      { priority: 4, action: 'Conduct training session', timeframe: 'Mid-term (1 month)' },
      { priority: 5, action: 'Schedule first process audit', timeframe: 'Mid-term (6 weeks)' }
    ]
  }
}

router.post('/next-why', async (req, res) => {
  const { problem, issueType, whyLevel, previousAnswer, whyHistory } = req.body

  if (!problem || !whyLevel) {
    return res.status(400).json({ error: 'Missing required fields' })
  }

  const openaiKey = process.env.OPENAI_API_KEY
  if (!openaiKey || openaiKey === 'your_openai_api_key_here') {
    return res.json({
      question: getFallbackQuestion(whyLevel, previousAnswer),
      answers: getFallbackAnswers(whyLevel, previousAnswer),
      usedFallback: true
    })
  }

  try {
    const openai = new OpenAI({ apiKey: openaiKey })

    const historyText = (whyHistory || [])
      .map((h, i) => `Why ${i + 1}: Q: "${h.question}" A: "${h.answer}"`)
      .join('\n')

    const userPrompt = `Issue type: ${issueType || 'business'}
Original problem: "${problem}"
${historyText ? `Previous Why chain:\n${historyText}\n` : ''}
Now generate Why ${whyLevel} question and 5 possible answers.
${previousAnswer ? `The user's previous answer was: "${previousAnswer}"` : ''}

Respond with ONLY this JSON structure:
{
  "question": "short direct question max 10 words",
  "answers": ["answer 1", "answer 2", "answer 3", "answer 4", "answer 5"]
}`

    const completion = await openai.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user', content: userPrompt }
      ],
      temperature: 0.7,
      max_tokens: 400,
      response_format: { type: 'json_object' }
    })

    const content = completion.choices[0].message.content
    const parsed = JSON.parse(content)

    res.json({
      question: parsed.question || getFallbackQuestion(whyLevel, previousAnswer),
      answers: parsed.answers || getFallbackAnswers(whyLevel, previousAnswer),
      usedFallback: false
    })
  } catch (err) {
    console.error('OpenAI error:', err.message)
    res.json({
      question: getFallbackQuestion(whyLevel, previousAnswer),
      answers: getFallbackAnswers(whyLevel, previousAnswer),
      usedFallback: true
    })
  }
})

router.post('/conclusion', async (req, res) => {
  const { problem, issueType, whyPath } = req.body

  if (!problem || !whyPath) {
    return res.status(400).json({ error: 'Missing required fields' })
  }

  const openaiKey = process.env.OPENAI_API_KEY
  if (!openaiKey || openaiKey === 'your_openai_api_key_here') {
    return res.json({ ...getFallbackConclusion(problem, whyPath), usedFallback: true })
  }

  try {
    const openai = new OpenAI({ apiKey: openaiKey })

    const whyText = whyPath
      .map((h, i) => `Why ${i + 1}: Q: "${h.question}" A: "${h.answer}"`)
      .join('\n')

    const userPrompt = `Issue type: ${issueType || 'business'}
Original problem: "${problem}"

5 Why chain:
${whyText}

Generate a complete root cause analysis conclusion.

Respond with ONLY this JSON:
{
  "short": "3-5 sentence short conclusion identifying root cause and first improvement",
  "rootCauseCategory": "one of: Process failure, Communication failure, Training gap, Tool/resource issue, Human error, Management issue, Planning issue, Documentation issue, Quality control issue, Follow-up failure, System weakness",
  "problemSummary": "1-2 sentence problem summary",
  "mostLikelyRootCause": "concise root cause statement",
  "contributingFactors": ["factor 1", "factor 2", "factor 3", "factor 4"],
  "correctiveActions": ["action 1", "action 2", "action 3", "action 4"],
  "preventiveActions": ["action 1", "action 2", "action 3", "action 4"],
  "actionPlan": [
    {"priority": 1, "action": "action description", "timeframe": "timeframe"},
    {"priority": 2, "action": "action description", "timeframe": "timeframe"},
    {"priority": 3, "action": "action description", "timeframe": "timeframe"}
  ]
}`

    const completion = await openai.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user', content: userPrompt }
      ],
      temperature: 0.5,
      max_tokens: 1000,
      response_format: { type: 'json_object' }
    })

    const content = completion.choices[0].message.content
    const parsed = JSON.parse(content)

    res.json({
      short: parsed.short,
      rootCauseCategory: parsed.rootCauseCategory,
      problemSummary: parsed.problemSummary || problem,
      whyPath,
      mostLikelyRootCause: parsed.mostLikelyRootCause,
      contributingFactors: parsed.contributingFactors || [],
      correctiveActions: parsed.correctiveActions || [],
      preventiveActions: parsed.preventiveActions || [],
      actionPlan: parsed.actionPlan || [],
      usedFallback: false
    })
  } catch (err) {
    console.error('OpenAI error:', err.message)
    res.json({ ...getFallbackConclusion(problem, whyPath), usedFallback: true })
  }
})

export { router as analyzeRoute }
