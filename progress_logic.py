class ProgressGate:
    @staticmethod
    def calculate(data, assets_ready, mc_ready):
        """Calculates 12-point progress score."""
        score = 0
        if data.get('client'): score += 1
        if data.get('project'): score += 1
        if data.get('venue'): score += 1
        if data.get('year'): score += 1
        if data.get('month'): score += 1
        if data.get('category'): score += 1
        if data.get('what_we_do'): score += 1
        if data.get('scope'): score += 1
        if data.get('open_question'): score += 1
        if assets_ready: score += 2
        if mc_ready: score += 1
        return int((score / 12) * 100)
