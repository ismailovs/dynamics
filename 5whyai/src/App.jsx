import { useAnalysis, SCREENS } from './hooks/useAnalysis.js'
import TopBar from './components/TopBar.jsx'
import WelcomeScreen from './components/WelcomeScreen.jsx'
import IssueTypeScreen from './components/IssueTypeScreen.jsx'
import ProblemInputScreen from './components/ProblemInputScreen.jsx'
import WhyQuestionScreen from './components/WhyQuestionScreen.jsx'
import ConclusionScreen from './components/ConclusionScreen.jsx'
import FullConclusionScreen from './components/FullConclusionScreen.jsx'
import HistoryScreen from './components/HistoryScreen.jsx'

export default function App() {
  const {
    screen,
    state,
    startNewAnalysis,
    selectIssueType,
    startAnalysis,
    submitAnswer,
    viewFullConclusion,
    goToHistory,
    goBack,
    loadAnalysis,
    setScreen
  } = useAnalysis()

  const renderScreen = () => {
    switch (screen) {
      case SCREENS.WELCOME:
        return (
          <WelcomeScreen
            onStart={startNewAnalysis}
            onHistory={goToHistory}
          />
        )

      case SCREENS.ISSUE_TYPE:
        return (
          <IssueTypeScreen
            onSelect={selectIssueType}
            onBack={goBack}
          />
        )

      case SCREENS.PROBLEM_INPUT:
        return (
          <ProblemInputScreen
            issueType={state.issueType}
            onSubmit={startAnalysis}
            onBack={goBack}
            loading={state.loading}
          />
        )

      case SCREENS.WHY_QUESTION:
        return (
          <WhyQuestionScreen
            whyLevel={state.currentWhyLevel}
            question={state.currentQuestion}
            answers={state.currentAnswers}
            problem={state.problem}
            whyPath={state.whyPath}
            onAnswer={submitAnswer}
            loading={state.loading}
            error={state.error}
          />
        )

      case SCREENS.CONCLUSION:
        return (
          <ConclusionScreen
            conclusion={state.conclusion}
            problem={state.problem}
            issueType={state.issueType}
            whyPath={state.whyPath}
            onFullConclusion={viewFullConclusion}
            onNewAnalysis={startNewAnalysis}
          />
        )

      case SCREENS.FULL_CONCLUSION:
        return (
          <FullConclusionScreen
            conclusion={state.conclusion}
            problem={state.problem}
            issueType={state.issueType}
            whyPath={state.whyPath}
            onBack={goBack}
            onNewAnalysis={startNewAnalysis}
          />
        )

      case SCREENS.HISTORY:
        return (
          <HistoryScreen
            onBack={goBack}
            onLoad={loadAnalysis}
            onNewAnalysis={startNewAnalysis}
          />
        )

      default:
        return null
    }
  }

  return (
    <div className="app-shell">
      <TopBar
        screen={screen}
        onNew={startNewAnalysis}
        onHistory={goToHistory}
      />
      {renderScreen()}
    </div>
  )
}
