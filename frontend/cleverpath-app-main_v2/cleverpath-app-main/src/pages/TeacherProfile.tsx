import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { getTeacherStudents, toggleStudentRL, StudentProgress } from '@/services/api';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Users, TrendingUp, Clock, Award, Brain, BookOpen, FileText, HelpCircle, Layout, ArrowRight } from 'lucide-react';
import { toast } from 'sonner';

const TeacherProfile = () => {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [students, setStudents] = useState<StudentProgress[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadStudents();
    }, []);

    const loadStudents = async () => {
        try {
            const data = await getTeacherStudents();
            setStudents(data);
        } catch (error) {
            console.error('Failed to load students:', error);
            toast.error('Failed to load student data');
        } finally {
            setLoading(false);
        }
    };

    const handleRLToggle = async (studentId: string, enrollmentId: string, currentState: boolean) => {
        try {
            await toggleStudentRL(enrollmentId, !currentState);

            // Update local state by enrollment_id, not student_id
            setStudents(students.map(s =>
                s.enrollment_id === enrollmentId ? { ...s, rl_enabled: !currentState } : s
            ));

            toast.success(`RL agent ${!currentState ? 'enabled' : 'disabled'} for student`);
        } catch (error) {
            console.error('Failed to toggle RL:', error);
            toast.error('Failed to update RL setting');
        }
    };

    if (loading) {
        return (
            <div className="flex min-h-[60vh] items-center justify-center">
                <div className="text-center">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto mb-4"></div>
                    <p className="text-muted-foreground">Loading dashboard...</p>
                </div>
            </div>
        );
    }

    const totalStudents = students.length;
    const avgCompletionRate = students.length > 0
        ? Math.round(students.reduce((sum, s) => sum + s.lessons_completed, 0) / students.length)
        : 0;
    const avgScore = students.length > 0
        ? Math.round(students.reduce((sum, s) => sum + s.average_score, 0) / students.length * 100)
        : 0;
    const rlEnabledCount = students.filter(s => s.rl_enabled).length;

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="space-y-2">
                <h1 className="text-4xl font-bold tracking-tight">Teacher Dashboard</h1>
                <p className="text-xl text-muted-foreground">Welcome, {user?.full_name}</p>
            </div>

            {/* Stats Overview */}
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                <Card className="p-6 bg-gradient-to-br from-primary/10 to-primary/5 border-primary/20">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-muted-foreground">Total Students</p>
                            <p className="text-3xl font-bold">{totalStudents}</p>
                        </div>
                        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
                            <Users className="h-6 w-6 text-primary" />
                        </div>
                    </div>
                </Card>

                <Card className="p-6 bg-gradient-to-br from-secondary/10 to-secondary/5 border-secondary/20">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-muted-foreground">Avg Completion</p>
                            <p className="text-3xl font-bold">{avgCompletionRate}</p>
                        </div>
                        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-secondary/10">
                            <TrendingUp className="h-6 w-6 text-secondary" />
                        </div>
                    </div>
                </Card>

                <Card className="p-6 bg-gradient-to-br from-accent/10 to-accent/5 border-accent/20">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-muted-foreground">Avg Score</p>
                            <p className="text-3xl font-bold">{avgScore}%</p>
                        </div>
                        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-accent/10">
                            <Award className="h-6 w-6 text-accent" />
                        </div>
                    </div>
                </Card>

                <Card className="p-6 bg-gradient-to-br from-success/10 to-success/5 border-success/20">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-muted-foreground">RL Enabled</p>
                            <p className="text-3xl font-bold">{rlEnabledCount}</p>
                        </div>
                        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-success/10">
                            <Brain className="h-6 w-6 text-success" />
                        </div>
                    </div>
                </Card>
            </div>

            {/* Content Management Section */}
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <div>
                        <h2 className="text-2xl font-semibold">Content Management</h2>
                        <p className="text-muted-foreground">Create and manage your educational content</p>
                    </div>
                </div>

                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                    {/* Manage Content Card */}
                    <Card className="p-6 bg-card border-border hover:shadow-[var(--shadow-elevated)] transition-all cursor-pointer group"
                        onClick={() => navigate('/teacher/content')}>
                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 group-hover:bg-primary/20 transition-colors">
                                    <Layout className="h-6 w-6 text-primary" />
                                </div>
                                <ArrowRight className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />
                            </div>
                            <div>
                                <h3 className="font-semibold mb-1">Manage Content</h3>
                                <p className="text-sm text-muted-foreground">
                                    Overview dashboard for all your content
                                </p>
                            </div>
                            <Button
                                variant="outline"
                                className="w-full group-hover:bg-primary group-hover:text-primary-foreground transition-colors"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    navigate('/teacher/content');
                                }}
                            >
                                Open Dashboard
                            </Button>
                        </div>
                    </Card>

                    {/* Subject Manager Card */}
                    <Card className="p-6 bg-card border-border hover:shadow-[var(--shadow-elevated)] transition-all cursor-pointer group"
                        onClick={() => navigate('/teacher/subjects')}>
                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-secondary/10 group-hover:bg-secondary/20 transition-colors">
                                    <BookOpen className="h-6 w-6 text-secondary" />
                                </div>
                                <ArrowRight className="h-5 w-5 text-muted-foreground group-hover:text-secondary transition-colors" />
                            </div>
                            <div>
                                <h3 className="font-semibold mb-1">Subjects</h3>
                                <p className="text-sm text-muted-foreground">
                                    Create and manage course subjects
                                </p>
                            </div>
                            <Button
                                variant="outline"
                                className="w-full group-hover:bg-secondary group-hover:text-secondary-foreground transition-colors"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    navigate('/teacher/subjects');
                                }}
                            >
                                Manage Subjects
                            </Button>
                        </div>
                    </Card>

                    {/* Lesson Editor Card */}
                    <Card className="p-6 bg-card border-border hover:shadow-[var(--shadow-elevated)] transition-all cursor-pointer group"
                        onClick={() => navigate('/teacher/lessons')}>
                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-accent/10 group-hover:bg-accent/20 transition-colors">
                                    <FileText className="h-6 w-6 text-accent" />
                                </div>
                                <ArrowRight className="h-5 w-5 text-muted-foreground group-hover:text-accent transition-colors" />
                            </div>
                            <div>
                                <h3 className="font-semibold mb-1">Lessons</h3>
                                <p className="text-sm text-muted-foreground">
                                    Create and edit lesson content
                                </p>
                            </div>
                            <Button
                                variant="outline"
                                className="w-full group-hover:bg-accent group-hover:text-accent-foreground transition-colors"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    navigate('/teacher/lessons');
                                }}
                            >
                                Edit Lessons
                            </Button>
                        </div>
                    </Card>

                    {/* Question Bank Card */}
                    <Card className="p-6 bg-card border-border hover:shadow-[var(--shadow-elevated)] transition-all cursor-pointer group"
                        onClick={() => navigate('/teacher/questions')}>
                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-success/10 group-hover:bg-success/20 transition-colors">
                                    <HelpCircle className="h-6 w-6 text-success" />
                                </div>
                                <ArrowRight className="h-5 w-5 text-muted-foreground group-hover:text-success transition-colors" />
                            </div>
                            <div>
                                <h3 className="font-semibold mb-1">Questions</h3>
                                <p className="text-sm text-muted-foreground">
                                    Manage quiz questions and answers
                                </p>
                            </div>
                            <Button
                                variant="outline"
                                className="w-full group-hover:bg-success group-hover:text-success-foreground transition-colors"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    navigate('/teacher/questions');
                                }}
                            >
                                Manage Questions
                            </Button>
                        </div>
                    </Card>

                    {/* Groups Card */}
                    <Card className="p-6 bg-card border-border hover:shadow-[var(--shadow-elevated)] transition-all cursor-pointer group"
                        onClick={() => navigate('/teacher/groups')}>
                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-accent/10 group-hover:bg-accent/20 transition-colors">
                                    <Users className="h-6 w-6 text-accent" />
                                </div>
                                <ArrowRight className="h-5 w-5 text-muted-foreground group-hover:text-accent transition-colors" />
                            </div>
                            <div>
                                <h3 className="font-semibold mb-1">Groups</h3>
                                <p className="text-sm text-muted-foreground">
                                    Organize students into groups
                                </p>
                            </div>
                            <Button
                                variant="outline"
                                className="w-full group-hover:bg-accent group-hover:text-accent-foreground transition-colors"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    navigate('/teacher/groups');
                                }}
                            >
                                Manage Groups
                            </Button>
                        </div>
                    </Card>
                </div>
            </div>

            {/* Students Table */}
            <Card className="p-6 bg-card border-border">
                <div className="space-y-4">
                    <h2 className="text-2xl font-semibold">Student Progress</h2>

                    {students.length === 0 ? (
                        <div className="text-center py-8">
                            <p className="text-muted-foreground">No students enrolled yet.</p>
                        </div>
                    ) : (
                        <div className="rounded-lg border border-border overflow-hidden">
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>Student</TableHead>
                                        <TableHead>Subject</TableHead>
                                        <TableHead className="text-center">Lessons</TableHead>
                                        <TableHead className="text-center">Quizzes</TableHead>
                                        <TableHead className="text-center">Avg Score</TableHead>
                                        <TableHead className="text-center">Time Spent</TableHead>
                                        <TableHead className="text-center">Last Activity</TableHead>
                                        <TableHead className="text-center">RL Agent</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {students.map((student) => (
                                        <TableRow key={student.enrollment_id}>
                                            <TableCell>
                                                <div>
                                                    <div className="font-medium">{student.student_name}</div>
                                                    <div className="text-sm text-muted-foreground">{student.student_email}</div>
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                <Badge variant="outline" className="font-normal">
                                                    {student.subject_name}
                                                </Badge>
                                            </TableCell>
                                            <TableCell className="text-center">
                                                <Badge variant="outline">{student.lessons_completed}</Badge>
                                            </TableCell>
                                            <TableCell className="text-center">
                                                <Badge variant="outline">{student.quizzes_completed}</Badge>
                                            </TableCell>
                                            <TableCell className="text-center">
                                                <Badge className={student.average_score >= 0.8 ? 'bg-success/10 text-success' : 'bg-muted'}>
                                                    {Math.round(student.average_score * 100)}%
                                                </Badge>
                                            </TableCell>
                                            <TableCell className="text-center">
                                                <div className="flex items-center justify-center space-x-1 text-sm text-muted-foreground">
                                                    <Clock className="h-4 w-4" />
                                                    <span>{Math.round(student.total_time_seconds / 3600)}h</span>
                                                </div>
                                            </TableCell>
                                            <TableCell className="text-center text-sm text-muted-foreground">
                                                {student.last_activity
                                                    ? new Date(student.last_activity).toLocaleDateString()
                                                    : 'Never'}
                                            </TableCell>
                                            <TableCell className="text-center">
                                                <div className="flex items-center justify-center space-x-2">
                                                    <Switch
                                                        checked={student.rl_enabled}
                                                        onCheckedChange={() => handleRLToggle(student.student_id, student.enrollment_id, student.rl_enabled)}
                                                    />
                                                    {student.rl_enabled && (
                                                        <Badge className="bg-gradient-to-r from-primary to-primary-glow text-xs">
                                                            ON
                                                        </Badge>
                                                    )}
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </div>
                    )}
                </div>
            </Card>

            {/* Info Card */}
            <Card className="p-6 bg-gradient-to-br from-primary/10 to-accent/10 border-primary/20">
                <div className="flex items-start space-x-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                        <Brain className="h-5 w-5 text-primary" />
                    </div>
                    <div className="flex-1">
                        <h3 className="font-semibold mb-1">RL Agent Control</h3>
                        <p className="text-sm text-muted-foreground">
                            Toggle the RL (Reinforcement Learning) agent for individual students to enable or disable adaptive learning.
                            When enabled, the system uses AI to personalize question difficulty and learning paths.
                        </p>
                    </div>
                </div>
            </Card>
        </div>
    );
};

export default TeacherProfile;
