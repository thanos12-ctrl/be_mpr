import { useEffect, useState } from 'react';
import { getTeacherStudents, toggleStudentRL, fetchAdminSubjects, StudentProgress as StudentProgressType, Subject } from '@/services/api';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Users, TrendingUp, Clock, Award, Brain } from 'lucide-react';
import { toast } from 'sonner';

const StudentProgress = () => {
    const [students, setStudents] = useState<StudentProgressType[]>([]);
    const [subjects, setSubjects] = useState<Subject[]>([]);
    const [selectedSubjectId, setSelectedSubjectId] = useState<string>('');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const [studentsData, subjectsData] = await Promise.all([
                getTeacherStudents(),
                fetchAdminSubjects()
            ]);
            setStudents(studentsData);
            setSubjects(subjectsData);
        } catch (error) {
            console.error('Failed to load data:', error);
            toast.error('Failed to load data');
        } finally {
            setLoading(false);
        }
    };

    const handleRLToggle = async (studentId: string, enrollmentId: string, currentState: boolean) => {
        try {
            await toggleStudentRL(enrollmentId, !currentState);

            // Update local state by enrollment_id
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
                    <p className="text-muted-foreground">Loading student progress...</p>
                </div>
            </div>
        );
    }

    const filteredStudents = selectedSubjectId 
        ? students.filter(s => s.subject_id === selectedSubjectId)
        : students;

    const totalStudents = filteredStudents.length;
    const avgCompletionRate = filteredStudents.length > 0
        ? Math.round(filteredStudents.reduce((sum, s) => sum + s.lessons_completed, 0) / filteredStudents.length)
        : 0;
    const avgScore = filteredStudents.length > 0
        ? Math.round(filteredStudents.reduce((sum, s) => sum + s.average_score, 0) / filteredStudents.length * 100)
        : 0;
    const rlEnabledCount = filteredStudents.filter(s => s.rl_enabled).length;

    return (
        <div className="space-y-8">
            <div className="space-y-2">
                <h1 className="text-4xl font-bold tracking-tight">Student Progress</h1>
                <p className="text-xl text-muted-foreground">Monitor performance and manage adaptive learning</p>
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                <Card className="p-6 bg-card border-border">
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

                <Card className="p-6 bg-card border-border">
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

                <Card className="p-6 bg-card border-border">
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

                <Card className="p-6 bg-card border-border">
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

            <Card className="p-6 bg-card border-border">
                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <h2 className="text-2xl font-semibold">Enrolled Students</h2>
                        <div className="w-[250px]">
                            <select
                                className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                                value={selectedSubjectId}
                                onChange={(e) => setSelectedSubjectId(e.target.value)}
                            >
                                <option value="">All Subjects</option>
                                {subjects.map(subject => (
                                    <option key={subject.id} value={subject.id}>
                                        {subject.name}
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>

                    {filteredStudents.length === 0 ? (
                        <div className="text-center py-8">
                            <p className="text-muted-foreground">No students found matching your criteria.</p>
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
                                    {filteredStudents.map((student) => (
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

export default StudentProgress;
