class ProgressGate:
    @staticmethod
    def calculate(data, assets_ready, mc_ready):
        """12-Point Completion Check Logic."""
        score = 0
        # Text Fields (5)
        if data.get('client'): score += 1
        if data.get('project'): score += 1
        if data.get('venue'): score += 1
        if data.get('year'): score += 1
        if data.get('month'): score += 1
        
        # Frameworks (3)
        if data.get('category'): score += 1
        if data.get('what_we_do'): score += 1
        if data.get('scope'): score += 1
        
        # Strategy (1)
        if data.get('open_question'): score += 1
        
        # Visuals (2)
        if assets_ready: score += 2
        
        # AI Diagnostic (1)
        if mc_ready: score += 1
        
        return int((score / 12) * 100)
