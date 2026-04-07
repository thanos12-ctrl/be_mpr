import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { BookOpen, Clock, Award } from 'lucide-react';
import { fetchSubjects, fetchLessons, Subject, Lesson } from '@/services/api';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';

const Chapters = () => {
  const [searchParams] = useSearchParams();
  const subjectFilter = searchParams.get('subject');

  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [subjectsData, lessonsData] = await Promise.all([
          fetchSubjects(),
          fetchLessons()
        ]);
        setSubjects(subjectsData);
        setLessons(lessonsData);
      } catch (error) {
        console.error('Failed to load data:', error);
        toast.error('Failed to load subjects and lessons');
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const getDifficultyColor = (difficulty: number) => {
    if (difficulty <= 0.3) return 'bg-success text-success-foreground';
    if (difficulty <= 0.7) return 'bg-secondary text-secondary-foreground';
    return 'bg-destructive text-destructive-foreground';
  };

  const getDifficultyLabel = (difficulty: number) => {
    if (difficulty <= 0.3) return 'Beginner';
    if (difficulty <= 0.7) return 'Intermediate';
    return 'Advanced';
  };

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading lessons...</p>
        </div>
      </div>
    );
  }

  if (lessons.length === 0) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <BookOpen className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
          <h2 className="text-2xl font-semibold mb-2">No Lessons Available</h2>
          <p className="text-muted-foreground">
            Check back later for new learning content!
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h1 className="text-4xl font-bold tracking-tight">
          {subjectFilter
            ? subjects.find(s => s.id === subjectFilter)?.name || 'Your Learning Journey'
            : 'Your Learning Journey'
          }
        </h1>
        <p className="text-xl text-muted-foreground">
          Choose a lesson to continue your adaptive learning experience
        </p>
      </div>

      {subjects.map((subject) => {
        // Filter by subject if query param is present
        if (subjectFilter && subject.id !== subjectFilter) {
          return null;
        }

        const subjectLessons = lessons.filter(l => l.subject_id === subject.id);

        if (subjectLessons.length === 0) return null;

        return (
          <div key={subject.id} className="space-y-4">
            <div className="flex items-center space-x-3">
              <span className="text-3xl">{subject.icon}</span>
              <div>
                <h2 className="text-2xl font-semibold">{subject.name}</h2>
                <p className="text-sm text-muted-foreground">{subject.description}</p>
              </div>
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {subjectLessons.map((lesson) => (
                <Link key={lesson.id} to={`/topic/${lesson.id}`}>
                  <Card className="group h-full overflow-hidden border-border bg-card transition-all duration-300 hover:shadow-[var(--shadow-elevated)] hover:-translate-y-1">
                    <div className="h-2 bg-gradient-to-r from-primary to-primary-glow" />

                    <div className="p-6 space-y-4">
                      <div className="flex items-start justify-between">
                        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-primary-glow">
                          <BookOpen className="h-6 w-6 text-primary-foreground" />
                        </div>
                        <Badge className={getDifficultyColor(lesson.difficulty_level)}>
                          {getDifficultyLabel(lesson.difficulty_level)}
                        </Badge>
                      </div>

                      <div className="space-y-2">
                        <div className="flex items-center space-x-2">
                          <span className="text-xs font-semibold text-primary">Lesson {lesson.lesson_number}</span>
                        </div>
                        <h3 className="text-xl font-semibold group-hover:text-primary transition-colors">
                          {lesson.title}
                        </h3>
                        <p className="text-sm text-muted-foreground line-clamp-2">
                          {lesson.introduction}
                        </p>
                      </div>

                      <div className="flex items-center justify-between pt-2 border-t border-border text-sm text-muted-foreground">
                        <div className="flex items-center space-x-1">
                          <Clock className="h-4 w-4" />
                          <span>{lesson.estimated_time_minutes} min</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <Award className="h-4 w-4" />
                          <span>{lesson.key_takeaways.length} takeaways</span>
                        </div>
                      </div>
                    </div>
                  </Card>
                </Link>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default Chapters;
