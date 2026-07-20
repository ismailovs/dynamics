import express from 'express'
import cors from 'cors'
import { config } from 'dotenv'
import { analyzeRoute } from './routes/analyze.js'

config()

const app = express()
const PORT = process.env.PORT || 3001

app.use(cors())
app.use(express.json())

app.use('/api', analyzeRoute)

app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() })
})

app.listen(PORT, () => {
  console.log(`5WhyAI server running on port ${PORT}`)
})
