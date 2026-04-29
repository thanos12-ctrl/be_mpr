import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { CheckCircle2, Circle, ArrowRight, Brain, XCircle, Lightbulb } from 'lucide-react';
import { startLessonQuizSession, getNextQuestion, submitAnswer, QuizQuestion, QuizFeedback } from '@/services/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';

const Quiz = () => {
  const { bundleId } = useParams<{ bundleId: string }>();
  const navigate = useNavigate();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<QuizQuestion | null>(null);
  const [selectedAnswer, setSelectedAnswer] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<QuizFeedback | null>(null);
  const [questionStartTime, setQuestionStartTime] = useState<number>(Date.now());

  useEffect(() => {
    const initQuiz = async () => {
      if (bundleId) {
        try {
          const session = await startLessonQuizSession(bundleId, 10);
          setSessionId(session.session_id);

          // Get first question
          const question = await getNextQuestion(session.session_id);
          setCurrentQuestion(question);
          setQuestionStartTime(Date.now());
        } catch (error) {
          console.error('Failed to start quiz:', error);
          toast.error('Failed to start quiz session');
        } finally {
          setLoading(false);
        }
      }
    };
    initQuiz();
  }, [bundleId]);

  const handleSelectAnswer = (answer: string) => {
    setSelectedAnswer(answer);
  };

  const handleSubmitAnswer = async () => {
    if (!sessionId || !currentQuestion || !selectedAnswer) return;

    setSubmitting(true);
    const timeElapsed = Date.now() - questionStartTime;

    try {
      const feedbackData: QuizFeedback = await submitAnswer(
        sessionId,
        currentQuestion.question_id,
        selectedAnswer,
        timeElapsed
      );

      setFeedback(feedbackData);
    } catch (error) {
      console.error('Failed to submit answer:', error);
      toast.error('Failed to submit answer');
    } finally {
      setSubmitting(false);
    }
  };

  const handleNextQuestion = () => {
    if (!feedback) return;

    if (feedback.should_continue && feedback.next_question) {
      setCurrentQuestion(feedback.next_question);
      setSelectedAnswer('');
      setFeedback(null);
      setQuestionStartTime(Date.now());
    } else {
      // Quiz completed, navigate to results
      toast.success('Quiz completed!');
      navigate(`/results/${sessionId}`);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading quiz...</p>
        </div>
      </div>
    );
  }

  if (!currentQuestion) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <p className="text-xl text-muted-foreground">Quiz not found</p>
        </div>
      </div>
    );
  }

  const progress = (currentQuestion.step / currentQuestion.total_steps) * 100;
  const canProceed = selectedAnswer !== '';

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">Adaptive Quiz</h1>
          <span className="text-sm font-medium text-muted-foreground">
            Question {currentQuestion.step} of {currentQuestion.total_steps}
          </span>
        </div>
        <Progress value={progress} className="h-2" />
      </div>

      <Card className="p-8 bg-card border-border shadow-[var(--shadow-card)]">
        <div className="space-y-6">
          <div className="space-y-3">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge className="bg-primary/10 text-primary text-xs">
                Difficulty: {Math.round(currentQuestion.difficulty * 100)}%
              </Badge>
              <Badge className="bg-secondary/10 text-secondary text-xs">
                Concept: {currentQuestion.concept}
              </Badge>
              <Badge className="bg-accent/10 text-accent text-xs">
                <Brain className="h-3 w-3 mr-1" />
                LSTM Confidence: {Math.round(currentQuestion.lstm_confidence * 100)}%
              </Badge>
            </div>
            <h2 className="text-2xl font-semibold">{currentQuestion.question_text}</h2>
            {currentQuestion.code && (
              <pre className="bg-muted p-4 rounded-lg overflow-x-auto">
                <code className="text-sm">{currentQuestion.code}</code>
              </pre>
            )}
          </div>

          <div className="space-y-3">
            {Object.entries(currentQuestion.options).map(([key, value]) => {
              const isSelected = selectedAnswer === key;
              const isSubmitted = !!feedback;
              const isCorrectOption = isSubmitted && feedback.correct_answer === key;
              const isIncorrectSelected = isSubmitted && isSelected && !feedback.is_correct;

              let buttonClass = 'border-border hover:border-primary/50 hover:bg-muted/50';
              let iconClass = 'text-muted-foreground';
              let Icon = Circle;

              if (isSubmitted) {
                if (isCorrectOption) {
                  buttonClass = 'border-green-500 bg-green-50/20';
                  iconClass = 'text-green-600';
                  Icon = CheckCircle2;
                } else if (isIncorrectSelected) {
                  buttonClass = 'border-red-500 bg-red-50/20';
                  iconClass = 'text-red-600';
                  Icon = XCircle;
                } else {
                  buttonClass = 'border-border opacity-50';
                  iconClass = 'text-muted-foreground';
                }
              } else if (isSelected) {
                buttonClass = 'border-primary bg-primary/5';
                iconClass = 'text-primary';
                Icon = CheckCircle2;
              }

              return (
                <button
                  key={key}
                  onClick={() => !isSubmitted && handleSelectAnswer(key)}
                  disabled={submitting || isSubmitted}
                  className={`w-full text-left p-4 rounded-lg border-2 transition-all duration-200 ${buttonClass}`}
                >
                  <div className="flex items-center space-x-3">
                    <Icon className={`h-5 w-5 flex-shrink-0 ${iconClass}`} />
                    <span className="text-base">
                      <strong>{key}:</strong> {value}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
          
          {feedback && (
            <div className="mt-6 p-5 rounded-lg border bg-yellow-50/50 border-yellow-200">
              <div className="flex gap-4">
                <div className="mt-1">
                  <Lightbulb className="h-6 w-6 text-yellow-500" />
                </div>
                <div>
                  <h4 className="text-yellow-600 font-bold text-xs tracking-wider mb-2 uppercase">Explanation</h4>
                  <p className="text-gray-800 leading-relaxed">
                    {feedback.is_correct ? (
                      <span className="text-green-600 font-semibold mr-2">Correct!</span>
                    ) : (
                      <span className="text-red-600 font-semibold mr-2">Incorrect.</span>
                    )}
                    {feedback.explanation}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </Card>

      <div className="flex justify-end">
        {!feedback ? (
          <Button
            onClick={handleSubmitAnswer}
            disabled={!canProceed || submitting}
            size="lg"
            className="bg-gradient-to-r from-primary to-primary-glow hover:opacity-90 transition-opacity"
          >
            {submitting ? 'Submitting...' : 'Submit Answer'}
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        ) : (
          <Button
            onClick={handleNextQuestion}
            size="lg"
            className="bg-gradient-to-r from-primary to-primary-glow hover:opacity-90 transition-opacity"
          >
            {feedback.should_continue ? 'Next Question' : 'Finish Quiz'}
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
};

export default Quiz;
