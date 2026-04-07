import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { BookOpen, GraduationCap, Users } from 'lucide-react';
import { toast } from 'sonner';

const Register = () => {
    const [fullName, setFullName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [role, setRole] = useState<'student' | 'teacher'>('student');
    const [loading, setLoading] = useState(false);
    const { register } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (password !== confirmPassword) {
            toast.error('Passwords do not match');
            return;
        }

        if (password.length < 8) {
            toast.error('Password must be at least 8 characters');
            return;
        }

        setLoading(true);

        try {
            await register(email, password, fullName, role);
            toast.success('Registration successful!');
            navigate('/subjects');
        } catch (error: any) {
            toast.error(error.response?.data?.detail || 'Registration failed. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-background p-4">
            <div className="w-full max-w-md space-y-8">
                <div className="text-center space-y-2">
                    <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-primary-glow mx-auto">
                        <BookOpen className="h-8 w-8 text-primary-foreground" />
                    </div>
                    <h1 className="text-3xl font-bold">Create Account</h1>
                    <p className="text-muted-foreground">Start your adaptive learning journey today</p>
                </div>

                <Card className="p-8 bg-card border-border shadow-[var(--shadow-card)]">
                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div className="space-y-2">
                            <Label htmlFor="fullName">Full Name</Label>
                            <Input
                                id="fullName"
                                type="text"
                                placeholder="John Doe"
                                value={fullName}
                                onChange={(e) => setFullName(e.target.value)}
                                required
                                disabled={loading}
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="email">Email</Label>
                            <Input
                                id="email"
                                type="email"
                                placeholder="you@example.com"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                                disabled={loading}
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="password">Password</Label>
                            <Input
                                id="password"
                                type="password"
                                placeholder="••••••••"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                disabled={loading}
                            />
                            <p className="text-xs text-muted-foreground">Must be at least 8 characters</p>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="confirmPassword">Confirm Password</Label>
                            <Input
                                id="confirmPassword"
                                type="password"
                                placeholder="••••••••"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                required
                                disabled={loading}
                            />
                        </div>

                        <div className="space-y-3">
                            <Label>I am a...</Label>
                            <RadioGroup value={role} onValueChange={(value) => setRole(value as 'student' | 'teacher')}>
                                <div className="flex items-center space-x-2 p-4 rounded-lg border-2 border-border hover:border-primary/50 transition-colors cursor-pointer">
                                    <RadioGroupItem value="student" id="student" />
                                    <Label htmlFor="student" className="flex items-center space-x-2 cursor-pointer flex-1">
                                        <GraduationCap className="h-5 w-5 text-primary" />
                                        <div>
                                            <div className="font-medium">Student</div>
                                            <div className="text-xs text-muted-foreground">Learn at your own pace</div>
                                        </div>
                                    </Label>
                                </div>

                                <div className="flex items-center space-x-2 p-4 rounded-lg border-2 border-border hover:border-primary/50 transition-colors cursor-pointer">
                                    <RadioGroupItem value="teacher" id="teacher" />
                                    <Label htmlFor="teacher" className="flex items-center space-x-2 cursor-pointer flex-1">
                                        <Users className="h-5 w-5 text-primary" />
                                        <div>
                                            <div className="font-medium">Teacher</div>
                                            <div className="text-xs text-muted-foreground">Manage students and track progress</div>
                                        </div>
                                    </Label>
                                </div>
                            </RadioGroup>
                        </div>

                        <Button
                            type="submit"
                            className="w-full bg-gradient-to-r from-primary to-primary-glow hover:opacity-90 transition-opacity"
                            disabled={loading}
                        >
                            {loading ? 'Creating account...' : 'Create Account'}
                        </Button>
                    </form>
                </Card>

                <div className="text-center text-sm">
                    <span className="text-muted-foreground">Already have an account? </span>
                    <Link to="/login" className="text-primary hover:underline font-medium">
                        Sign in
                    </Link>
                </div>
            </div>
        </div>
    );
};

export default Register;
