import { useState, useCallback } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { fetchNextWhy, fetchConclusion } from '../services/aiService.js'
import { saveAnalysis } from '../utils/storage.js'

export const SCREENS = {
  WELCOME: 'welcome',
  ISSUE_TYPE: 'issue_type',
  PROBLEM_INPUT: 'problem_input',
  WHY_QUESTION: 'why_question',
  CONCLUSION: 'conclusion',
  FULL_CONCLUSION: 'full_conclusion',
  HISTORY: 'history',
  SETTINGS: 'settings'
}

const initialState = {
  id: null,
  issueType: null,
  problem: '',
  whyPath: [],
  currentWhyLevel: 1,
  currentQuestion: '',
  currentAnswers: [],
  loading: false,
  error: null,
  conclusion: null
}

export function useAnalysis() {
  const [screen, setScreen] = useState(SCREENS.WELCOME)
  const [state, setState] = useState(initialState)

  const update = (patch) => setState(s => ({ ...s, ...patch }))

  const startNewAnalysis = useCallback(() => {
    setState({ ...initialState, id: uuidv4() })
    setScreen(SCREENS.ISSUE_TYPE)
  }, [])

  const selectIssueType = useCallback((issueType) => {
    update({ issueType })
    setScreen(SCREENS.PROBLEM_INPUT)
  }, [])

  const startAnalysis = useCallback(async (problem) => {
    update({ problem, loading: true, error: null, whyPath: [], currentWhyLevel: 1 })
    try {
      const data = await fetchNextWhy({
        problem,
        issueType: state.issueType,
        whyLevel: 1,
        previousAnswer: null,
        whyHistory: []
      })
      update({
        loading: false,
        currentQuestion: data.question,
        currentAnswers: data.answers
      })
      setScreen(SCREENS.WHY_QUESTION)
    } catch (err) {
      update({ loading: false, error: 'Failed to connect. Please try again.' })
    }
  }, [state.issueType])

  const submitAnswer = useCallback(async (answer) => {
    const newPath = [
      ...state.whyPath,
      { question: state.currentQuestion, answer }
    ]
    const nextLevel = state.currentWhyLevel + 1

    update({ loading: true, error: null })

    if (nextLevel > 5) {
      try {
        const conclusion = await fetchConclusion({
          problem: state.problem,
          issueType: state.issueType,
          whyPath: newPath
        })
        const analysisData = {
          id: state.id,
          issueType: state.issueType,
          problem: state.problem,
          whyPath: newPath,
          conclusion,
          createdAt: new Date().toISOString()
        }
        saveAnalysis(analysisData)
        update({
          loading: false,
          whyPath: newPath,
          conclusion,
          currentWhyLevel: nextLevel
        })
        setScreen(SCREENS.CONCLUSION)
      } catch (err) {
        update({ loading: false, error: 'Failed to generate conclusion. Please try again.' })
      }
    } else {
      try {
        const data = await fetchNextWhy({
          problem: state.problem,
          issueType: state.issueType,
          whyLevel: nextLevel,
          previousAnswer: answer,
          whyHistory: newPath
        })
        update({
          loading: false,
          whyPath: newPath,
          currentWhyLevel: nextLevel,
          currentQuestion: data.question,
          currentAnswers: data.answers
        })
      } catch (err) {
        update({ loading: false, error: 'Failed to load next question. Please try again.' })
      }
    }
  }, [state])

  const viewFullConclusion = useCallback(() => {
    setScreen(SCREENS.FULL_CONCLUSION)
  }, [])

  const goToHistory = useCallback(() => setScreen(SCREENS.HISTORY), [])
  const goToSettings = useCallback(() => setScreen(SCREENS.SETTINGS), [])
  const goBack = useCallback(() => {
    if (screen === SCREENS.FULL_CONCLUSION) setScreen(SCREENS.CONCLUSION)
    else if (screen === SCREENS.CONCLUSION) setScreen(SCREENS.WHY_QUESTION)
    else if (screen === SCREENS.WHY_QUESTION) {
      if (state.currentWhyLevel === 1) setScreen(SCREENS.PROBLEM_INPUT)
      // If mid-analysis, stay (no going back to previous why)
    }
    else if (screen === SCREENS.PROBLEM_INPUT) setScreen(SCREENS.ISSUE_TYPE)
    else if (screen === SCREENS.ISSUE_TYPE) setScreen(SCREENS.WELCOME)
    else if (screen === SCREENS.HISTORY || screen === SCREENS.SETTINGS) setScreen(SCREENS.WELCOME)
  }, [screen, state.currentWhyLevel])

  const loadAnalysis = useCallback((analysis) => {
    setState({
      ...initialState,
      id: analysis.id,
      issueType: analysis.issueType,
      problem: analysis.problem,
      whyPath: analysis.whyPath,
      currentWhyLevel: 6,
      conclusion: analysis.conclusion
    })
    setScreen(SCREENS.CONCLUSION)
  }, [])

  return {
    screen,
    state,
    startNewAnalysis,
    selectIssueType,
    startAnalysis,
    submitAnswer,
    viewFullConclusion,
    goToHistory,
    goToSettings,
    goBack,
    loadAnalysis,
    setScreen
  }
}
