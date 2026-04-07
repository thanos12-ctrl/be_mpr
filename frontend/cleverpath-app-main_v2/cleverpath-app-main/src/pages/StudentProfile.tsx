import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { getProgressOverview, getMyCourses, fetchSubjects, enrollInSubject, ProgressOverview, Enrollment, Subject } from '@/services/api';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { BookOpen, Trophy, Clock, TrendingUp, Zap, Plus } from 'lucide-react';
import { toast } from 'sonner';

const StudentProfile = () => {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [progress, setProgress] = useState<ProgressOverview | null>(null);
    const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
    const [subjects, setSubjects] = useState<Subject[]>([]);
    const [loading, setLoading] = useState(true);
    const [enrollingSubjectId, setEnrollingSubjectId] = useState<string | null>(null);

    // Create a map of subject_id to subject for easy lookup
    const subjectMap = subjects.reduce((acc, subject) => {
        acc[subject.id] = subject;
        return acc;
    }, {} as Record<string, Subject>);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const [progressData, enrollmentsData, subjectsData] = await Promise.all([
                getProgressOverview(),
                getMyCourses(),
                fetchSubjects(),
            ]);
            setProgress(progressData);
            setEnrollments(enrollmentsData);
            setSubjects(subjectsData);
        } catch (error) {
            console.error('Failed to load profile data:', error);
            toast.error('Failed to load profile data');
        } finally {
            setLoading(false);
        }
    };

    const handleEnroll = async (subjectId: string) => {
        setEnrollingSubjectId(subjectId);
        try {
            await enrollInSubject(subjectId);
            toast.success('Successfully enrolled in the course!');
            await loadData(); // Refresh data
        } catch (error: any) {
            console.error('Failed to enroll:', error);
            toast.error(error.response?.data?.detail || 'Failed to enroll in course');
        } finally {
            setEnrollingSubjectId(null);
        }
    };

    const handleCourseClick = (subjectId: string) => {
        navigate(`/subjects?subject=${subjectId}`);
    };

    // Filter out already enrolled subjects
    const enrolledSubjectIds = enrollments.map(e => e.subject_id);
    const availableSubjects = subjects.filter(s => !enrolledSubjectIds.includes(s.id));

    if (loading) {
        return (
            <div className="flex min-h-[60vh] items-center justify-center">
                <div className="text-center">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto mb-4"></div>
                    <p className="text-muted-foreground">Loading your profile...</p>
                </div>
            </div>
        );
    }

    const completionRate = progress
        ? Math.round((progress.completed_lessons / Math.max(progress.total_lessons, 1)) * 100)
        : 0;

    const hoursSpent = progress ? Math.round(progress.total_time_spent_seconds / 3600) : 0;

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="space-y-2">
                <h1 className="text-4xl font-bold tracking-tight">My Profile</h1>
                <p className="text-xl text-muted-foreground">Welcome back, {user?.full_name}!</p>
            </div>

            {/* Stats Overview */}
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                <Card className="p-6 bg-gradient-to-br from-primary/10 to-primary/5 border-primary/20">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-muted-foreground">Lessons Completed</p>
                            <p className="text-3xl font-bold">{progress?.completed_lessons || 0}</p>
                        </div>
                        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
                            <BookOpen className="h-6 w-6 text-primary" />
                        </div>
                    </div>
                </Card>

                <Card className="p-6 bg-gradient-to-br from-secondary/10 to-secondary/5 border-secondary/20">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-muted-foreground">Quizzes Taken</p>
                            <p className="text-3xl font-bold">{progress?.completed_quizzes || 0}</p>
                        </div>
                        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-secondary/10">
                            <Trophy className="h-6 w-6 text-secondary" />
                        </div>
                    </div>
                </Card>

                <Card className="p-6 bg-gradient-to-br from-accent/10 to-accent/5 border-accent/20">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-muted-foreground">Hours Spent</p>
                            <p className="text-3xl font-bold">{hoursSpent}</p>
                        </div>
                        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-accent/10">
                            <Clock className="h-6 w-6 text-accent" />
                        </div>
                    </div>
                </Card>

                <Card className="p-6 bg-gradient-to-br from-success/10 to-success/5 border-success/20">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-muted-foreground">Current Streak</p>
                            <p className="text-3xl font-bold">{progress?.current_streak_days || 0} days</p>
                        </div>
                        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-success/10">
                            <Zap className="h-6 w-6 text-success" />
                        </div>
                    </div>
                </Card>
            </div>

            {/* Progress Overview */}
            <Card className="p-8 bg-card border-border">
                <div className="space-y-6">
                    <div className="flex items-center justify-between">
                        <h2 className="text-2xl font-semibold">Overall Progress</h2>
                        <Badge className="bg-primary/10 text-primary border-primary/20">
                            {completionRate}% Complete
                        </Badge>
                    </div>

                    <div className="space-y-4">
                        <div className="space-y-2">
                            <div className="flex items-center justify-between text-sm">
                                <span className="text-muted-foreground">Lessons</span>
                                <span className="font-medium">
                                    {progress?.completed_lessons} / {progress?.total_lessons}
                                </span>
                            </div>
                            <Progress value={completionRate} className="h-3" />
                        </div>

                        <div className="space-y-2">
                            <div className="flex items-center justify-between text-sm">
                                <span className="text-muted-foreground">Average Quiz Score</span>
                                <span className="font-medium">{Math.round((progress?.average_quiz_score || 0) * 100)}%</span>
                            </div>
                            <Progress value={(progress?.average_quiz_score || 0) * 100} className="h-3" />
                        </div>
                    </div>
                </div>
            </Card>

            {/* Enrolled Courses */}
            <div className="space-y-4">
                <h2 className="text-2xl font-semibold">My Courses</h2>
                {enrollments.length === 0 ? (
                    <Card className="p-8 text-center">
                        <p className="text-muted-foreground">You haven't enrolled in any courses yet.</p>
                    </Card>
                ) : (
                    <div className="grid gap-4 md:grid-cols-2">
                        {enrollments.map((enrollment) => {
                            const subject = subjectMap[enrollment.subject_id];
                            const subjectName = subject?.name || 'Unknown Course';
                            const subjectIcon = subject?.icon || '📚';

                            return (
                                <Card
                                    key={enrollment.id}
                                    className="p-6 bg-card border-border hover:shadow-[var(--shadow-elevated)] transition-all cursor-pointer"
                                    onClick={() => handleCourseClick(enrollment.subject_id)}
                                >
                                    <div className="space-y-4">
                                        <div className="flex items-start justify-between">
                                            <div className="flex items-center space-x-3">
                                                <span className="text-3xl">{subjectIcon}</span>
                                                <div>
                                                    <h3 className="font-semibold text-lg">{subjectName}</h3>
                                                    <p className="text-sm text-muted-foreground">
                                                        Enrolled: {new Date(enrollment.enrolled_at).toLocaleDateString()}
                                                    </p>
                                                </div>
                                            </div>
                                            {enrollment.rl_enabled && (
                                                <Badge className="bg-gradient-to-r from-primary to-primary-glow">
                                                    <TrendingUp className="h-3 w-3 mr-1" />
                                                    AI Adaptive
                                                </Badge>
                                            )}
                                        </div>
                                        {enrollment.completed_at && (
                                            <Badge className="bg-success/10 text-success border-success/20">
                                                Completed {new Date(enrollment.completed_at).toLocaleDateString()}
                                            </Badge>
                                        )}
                                    </div>
                                </Card>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* Available Subjects */}
            {availableSubjects.length > 0 && (
                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <h2 className="text-2xl font-semibold">Available Subjects</h2>
                        <Badge variant="outline">{availableSubjects.length} subjects</Badge>
                    </div>
                    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                        {availableSubjects.map((subject) => (
                            <Card key={subject.id} className="p-6 bg-card border-border hover:shadow-[var(--shadow-elevated)] transition-all">
                                <div className="space-y-4">
                                    <div className="flex items-start justify-between">
                                        <div className="flex items-center space-x-3">
                                            <span className="text-4xl">{subject.icon}</span>
                                            <div>
                                                <h3 className="font-semibold text-lg">{subject.name}</h3>
                                                {subject.is_published && (
                                                    <Badge className="bg-success/10 text-success border-success/20 text-xs">
                                                        Published
                                                    </Badge>
                                                )}
                                            </div>
                                        </div>
                                    </div>

                                    <p className="text-sm text-muted-foreground line-clamp-2">
                                        {subject.description}
                                    </p>

                                    <Button
                                        onClick={() => handleEnroll(subject.id)}
                                        disabled={enrollingSubjectId === subject.id}
                                        className="w-full bg-gradient-to-r from-primary to-primary-glow hover:opacity-90 transition-opacity"
                                    >
                                        {enrollingSubjectId === subject.id ? (
                                            <>
                                                <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent mr-2"></div>
                                                Enrolling...
                                            </>
                                        ) : (
                                            <>
                                                <Plus className="h-4 w-4 mr-2" />
                                                Enroll Now
                                            </>
                                        )}
                                    </Button>
                                </div>
                            </Card>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default StudentProfile;
