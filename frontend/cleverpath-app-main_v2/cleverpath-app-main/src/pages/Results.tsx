import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Trophy, TrendingUp, Clock, Target, ArrowRight, Brain } from 'lucide-react';
import { getQuizProgress, QuizProgress } from '@/services/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const Results = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [results, setResults] = useState<QuizProgress | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadResults = async () => {
      if (sessionId) {
        try {
          const data = await getQuizProgress(sessionId);
          setResults(data);
        } catch (error) {
          console.error('Failed to load results:', error);
        } finally {
          setLoading(false);
        }
      }
    };
    loadResults();
  }, [sessionId]);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading results...</p>
        </div>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <p className="text-xl text-muted-foreground">Results not found</p>
        </div>
      </div>
    );
  }

  const scorePercentage = Math.round(results.overall_accuracy * 100);
  const minutesSpent = Math.round(results.time_spent_seconds / 60);

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-success';
    if (score >= 60) return 'text-secondary';
    return 'text-destructive';
  };

  const getScoreMessage = (score: number) => {
    if (score >= 90) return 'Outstanding! 🎉';
    if (score >= 80) return 'Great job! 👏';
    if (score >= 70) return 'Good work! 👍';
    if (score >= 60) return 'Keep practicing! 💪';
    return 'Need more practice 📚';
  };

  const getBundleId = (subject: string) => {
    if (subject.startsWith('lesson_')) {
      return subject.replace('lesson_', '');
    }
    return subject;
  };
  const bundleId = getBundleId(results.subject);

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div className="text-center space-y-4">
        <div className="inline-flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary-glow">
          <Trophy className="h-10 w-10 text-primary-foreground" />
        </div>
        <h1 className="text-4xl font-bold">Quiz Complete!</h1>
        <p className="text-xl text-muted-foreground">{getScoreMessage(scorePercentage)}</p>
      </div>

      {/* Score Overview */}
      <Card className="p-8 bg-gradient-to-br from-primary/10 to-accent/10 border-primary/20">
        <div className="text-center space-y-4">
          <div className={`text-6xl font-bold ${getScoreColor(scorePercentage)}`}>
            {scorePercentage}%
          </div>
          <p className="text-lg text-muted-foreground">Overall Accuracy</p>
          <Progress value={scorePercentage} className="h-3" />
        </div>
      </Card>

      {/* Revision Notice */}
      {scorePercentage < 70 && (
        <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
          <p className="text-destructive font-medium flex items-center justify-center">
            ⚠️ You scored below the 70% passing threshold. This lesson has not been marked as completed. Please revise the material and try again.
          </p>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid gap-6 md:grid-cols-3">
        <Card className="p-6 bg-card border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Questions</p>
              <p className="text-3xl font-bold">{results.total_questions_answered}</p>
            </div>
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
              <Target className="h-6 w-6 text-primary" />
            </div>
          </div>
        </Card>

        <Card className="p-6 bg-card border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Time Spent</p>
              <p className="text-3xl font-bold">{minutesSpent}m</p>
            </div>
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-secondary/10">
              <Clock className="h-6 w-6 text-secondary" />
            </div>
          </div>
        </Card>

        <Card className="p-6 bg-card border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Total Reward</p>
              <p className="text-3xl font-bold">{Math.round(results.total_reward)}</p>
            </div>
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-accent/10">
              <Trophy className="h-6 w-6 text-accent" />
            </div>
          </div>
        </Card>
      </div>

      {/* Concept Mastery */}
      <Card className="p-8 bg-card border-border">
        <div className="space-y-6">
          <div className="flex items-center space-x-2">
            <Brain className="h-6 w-6 text-primary" />
            <h2 className="text-2xl font-semibold">Concept Mastery</h2>
          </div>

          <div className="space-y-4">
            {Object.entries(results.concept_mastery).map(([concept, mastery]) => (
              <div key={concept} className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium capitalize">{concept.replace(/_/g, ' ')}</span>
                  <span className={getScoreColor(mastery * 100)}>
                    {Math.round(mastery * 100)}%
                  </span>
                </div>
                <Progress value={mastery * 100} className="h-2" />
              </div>
            ))}
          </div>
        </div>
      </Card>

      {/* Difficulty Progression */}
      {results.difficulty_progression.length > 0 && (
        <Card className="p-8 bg-card border-border">
          <div className="space-y-6">
            <div className="flex items-center space-x-2">
              <TrendingUp className="h-6 w-6 text-primary" />
              <h2 className="text-2xl font-semibold">Difficulty Progression</h2>
            </div>
            
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={results.difficulty_progression.map((diff, index) => ({ question: `Q${index + 1}`, difficulty: Math.round(diff * 100) }))}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.2} vertical={false} />
                  <XAxis 
                    dataKey="question" 
                    tick={{ fill: 'hsl(var(--foreground))' }} 
                    axisLine={{ stroke: 'hsl(var(--border))' }} 
                    tickLine={false} 
                  />
                  <YAxis 
                    domain={[0, 100]} 
                    tick={{ fill: 'hsl(var(--foreground))' }} 
                    axisLine={{ stroke: 'hsl(var(--border))' }} 
                    tickLine={false} 
                    tickFormatter={(value) => `${value}%`}
                  />
                  <Tooltip 
                    cursor={{ fill: 'hsl(var(--primary))', opacity: 0.1 }}
                    contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '8px', color: 'hsl(var(--foreground))' }}
                    itemStyle={{ color: 'hsl(var(--foreground))' }}
                    labelStyle={{ color: 'hsl(var(--foreground))' }}
                  />
                  <Bar 
                    dataKey="difficulty" 
                    fill="hsl(var(--primary))" 
                    radius={[4, 4, 0, 0]} 
                    name="Difficulty Level"
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="text-sm text-muted-foreground text-center">
              The AI adapted question difficulty based on your performance
            </p>
          </div>
        </Card>
      )}

      {/* Actions */}
      <div className="flex flex-col sm:flex-row gap-4 justify-center">
        <Link to="/subjects">
          <Button size="lg" variant="outline" className="w-full sm:w-auto">
            Back to Subjects
          </Button>
        </Link>
        {scorePercentage >= 70 ? (
          <Link to={`/subjects`}>
            <Button size="lg" className="bg-gradient-to-r from-success to-success/80 text-primary-foreground hover:opacity-90 transition-opacity w-full sm:w-auto">
              Proceed to Next Lesson
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </Link>
        ) : (
          <Link to={`/quiz/${bundleId}`}>
            <Button size="lg" className="bg-gradient-to-r from-primary to-primary-glow hover:opacity-90 transition-opacity w-full sm:w-auto">
              Try Again
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </Link>
        )}
      </div>
    </div>
  );
};

export default Results;
