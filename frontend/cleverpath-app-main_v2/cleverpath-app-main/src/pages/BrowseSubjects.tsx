import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchSubjects, getMyCourses, enrollInSubject, Subject, Enrollment } from '@/services/api';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { BookOpen, Plus, ArrowRight, CheckCircle } from 'lucide-react';
import { toast } from 'sonner';

const BrowseSubjects = () => {
    const navigate = useNavigate();
    const [subjects, setSubjects] = useState<Subject[]>([]);
    const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
    const [loading, setLoading] = useState(true);
    const [enrollingSubjectId, setEnrollingSubjectId] = useState<string | null>(null);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const [subjectsData, enrollmentsData] = await Promise.all([
                fetchSubjects(),
                getMyCourses(),
            ]);
            setSubjects(subjectsData);
            setEnrollments(enrollmentsData);
        } catch (error) {
            console.error('Failed to load subjects:', error);
            toast.error('Failed to load subjects');
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

    const handleStartLearning = (subjectId: string) => {
        navigate(`/subjects?subject=${subjectId}`);
    };

    // Create a set of enrolled subject IDs for quick lookup
    const enrolledSubjectIds = new Set(enrollments.map(e => e.subject_id));

    if (loading) {
        return (
            <div className="flex min-h-[60vh] items-center justify-center">
                <div className="text-center">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto mb-4"></div>
                    <p className="text-muted-foreground">Loading subjects...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="space-y-2">
                <h1 className="text-4xl font-bold tracking-tight">Browse Subjects</h1>
                <p className="text-xl text-muted-foreground">
                    Explore our courses and start your learning journey
                </p>
            </div>

            {/* Stats */}
            <div className="flex gap-6">
                <Card className="p-4 bg-gradient-to-br from-primary/10 to-primary/5 border-primary/20">
                    <div className="flex items-center space-x-3">
                        <BookOpen className="h-5 w-5 text-primary" />
                        <div>
                            <p className="text-sm text-muted-foreground">Total Subjects</p>
                            <p className="text-2xl font-bold">{subjects.length}</p>
                        </div>
                    </div>
                </Card>
                <Card className="p-4 bg-gradient-to-br from-success/10 to-success/5 border-success/20">
                    <div className="flex items-center space-x-3">
                        <CheckCircle className="h-5 w-5 text-success" />
                        <div>
                            <p className="text-sm text-muted-foreground">Enrolled</p>
                            <p className="text-2xl font-bold">{enrollments.length}</p>
                        </div>
                    </div>
                </Card>
            </div>

            {/* Subjects Grid */}
            {subjects.length === 0 ? (
                <Card className="p-8 text-center">
                    <BookOpen className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
                    <h2 className="text-2xl font-semibold mb-2">No Subjects Available</h2>
                    <p className="text-muted-foreground">
                        Check back later for new learning content!
                    </p>
                </Card>
            ) : (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                    {subjects.map((subject) => {
                        const isEnrolled = enrolledSubjectIds.has(subject.id);

                        return (
                            <Card
                                key={subject.id}
                                className="p-6 bg-card border-border hover:shadow-[var(--shadow-elevated)] transition-all"
                            >
                                <div className="space-y-4">
                                    {/* Header */}
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
                                        {isEnrolled && (
                                            <Badge className="bg-primary/10 text-primary border-primary/20">
                                                <CheckCircle className="h-3 w-3 mr-1" />
                                                Enrolled
                                            </Badge>
                                        )}
                                    </div>

                                    {/* Description */}
                                    <p className="text-sm text-muted-foreground line-clamp-3">
                                        {subject.description}
                                    </p>

                                    {/* Action Button */}
                                    {isEnrolled ? (
                                        <Button
                                            onClick={() => handleStartLearning(subject.id)}
                                            className="w-full bg-gradient-to-r from-primary to-primary-glow hover:opacity-90 transition-opacity"
                                        >
                                            <ArrowRight className="h-4 w-4 mr-2" />
                                            Start Learning
                                        </Button>
                                    ) : (
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
                                    )}
                                </div>
                            </Card>
                        );
                    })}
                </div>
            )}
        </div>
    );
};

export default BrowseSubjects;
