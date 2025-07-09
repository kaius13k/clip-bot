"""
Engagement Predictor MCP Server
Uses AI models to predict engagement potential of video segments
"""

import logging
from typing import Dict, Any, List, Optional
from .mcp_framework import AutoMCPServer, expose

logger = logging.getLogger(__name__)

class EngagementPredictor(AutoMCPServer):
    """Predicts engagement potential using AI models"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("EngagementPredictor")
        self.config = config
        self.ai_settings = config.get('ai_settings', {})
        
        # Model settings
        self.use_engagement_scoring = self.ai_settings.get('use_engagement_scoring', True)
        self.confidence_threshold = self.ai_settings.get('confidence_threshold', 0.8)
        
        # Models
        self.sentiment_model = None
        self.engagement_model = None
        self.models_loaded = False
        
        # Engagement keywords
        self.high_engagement_keywords = [
            'breaking', 'exclusive', 'shocking', 'amazing', 'incredible', 'viral',
            'must see', 'trending', 'hot', 'urgent', 'live', 'happening now',
            'first time', 'never seen', 'unbelievable', 'epic', 'massive',
            'announcement', 'reveal', 'launch', 'new', 'latest', 'update'
        ]
        
        self.educational_keywords = [
            'how to', 'tutorial', 'guide', 'learn', 'explain', 'tips',
            'tricks', 'hack', 'secret', 'method', 'technique', 'strategy',
            'review', 'analysis', 'breakdown', 'deep dive', 'explained'
        ]
        
        self.question_indicators = [
            'what', 'why', 'how', 'when', 'where', 'who', 'which',
            'question', 'answer', 'ask', 'wonder', 'curious'
        ]
    
    async def start(self):
        """Start the engagement predictor"""
        await super().start()
        
        if self.use_engagement_scoring:
            try:
                await self._load_models()
                logger.info("Engagement predictor models loaded")
            except Exception as e:
                logger.warning(f"Failed to load engagement models: {e}")
                logger.info("Falling back to keyword-based scoring")
                self.use_engagement_scoring = False
        
        logger.info("Engagement predictor started")
    
    async def _load_models(self):
        """Load AI models for engagement prediction"""
        try:
            from transformers import pipeline
            import asyncio
            
            loop = asyncio.get_event_loop()
            
            # Load sentiment analysis model
            self.sentiment_model = await loop.run_in_executor(
                None, 
                lambda: pipeline(
                    "sentiment-analysis",
                    model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                    return_all_scores=True
                )
            )
            
            # Load engagement classification model
            # Note: This is a placeholder - you would train a custom model for engagement
            self.engagement_model = await loop.run_in_executor(
                None,
                lambda: pipeline(
                    "text-classification",
                    model="unitary/toxic-bert",  # Placeholder - would use custom engagement model
                    return_all_scores=True
                )
            )
            
            self.models_loaded = True
            
        except ImportError:
            logger.warning("Transformers library not available")
            raise
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            raise
    
    @expose
    async def predict_engagement(self, transcript: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Predict engagement score for a transcript segment"""
        if not self.use_engagement_scoring or not transcript.strip():
            return self._keyword_based_scoring(transcript, metadata)
        
        try:
            if self.models_loaded:
                return await self._ai_based_scoring(transcript, metadata)
            else:
                return self._keyword_based_scoring(transcript, metadata)
        except Exception as e:
            logger.error(f"Error in engagement prediction: {e}")
            return self._keyword_based_scoring(transcript, metadata)
    
    async def _ai_based_scoring(self, transcript: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """AI-based engagement scoring"""
        import asyncio
        
        loop = asyncio.get_event_loop()
        
        # Get sentiment analysis
        sentiment_result = await loop.run_in_executor(
            None, self.sentiment_model, transcript
        )
        
        # Get engagement classification
        # Note: This would be a custom model trained on engagement data
        engagement_result = await loop.run_in_executor(
            None, self.engagement_model, transcript
        )
        
        # Process results
        sentiment_scores = {item['label']: item['score'] for item in sentiment_result[0]}
        engagement_scores = {item['label']: item['score'] for item in engagement_result[0]}
        
        # Calculate composite engagement score
        base_score = self._keyword_based_scoring(transcript, metadata)['engagement_score']
        
        # Sentiment weighting (positive sentiment = higher engagement)
        sentiment_multiplier = 1.0
        if 'POSITIVE' in sentiment_scores:
            sentiment_multiplier = 0.8 + (sentiment_scores['POSITIVE'] * 0.4)
        elif 'positive' in sentiment_scores:
            sentiment_multiplier = 0.8 + (sentiment_scores['positive'] * 0.4)
        
        # Apply AI adjustments
        ai_score = base_score * sentiment_multiplier
        
        # Confidence based on model certainty
        confidence = max(sentiment_scores.values()) if sentiment_scores else 0.5
        
        return {
            'engagement_score': min(ai_score, 10.0),  # Cap at 10
            'confidence': confidence,
            'method': 'ai_based',
            'sentiment_scores': sentiment_scores,
            'engagement_scores': engagement_scores,
            'base_keyword_score': base_score
        }
    
    def _keyword_based_scoring(self, transcript: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Keyword-based engagement scoring fallback"""
        text = transcript.lower()
        score = 0.0
        features = []
        
        # High engagement keywords
        high_eng_count = sum(1 for keyword in self.high_engagement_keywords if keyword in text)
        if high_eng_count > 0:
            score += high_eng_count * 1.5
            features.append(f"high_engagement_keywords({high_eng_count})")
        
        # Educational content
        edu_count = sum(1 for keyword in self.educational_keywords if keyword in text)
        if edu_count > 0:
            score += edu_count * 1.2
            features.append(f"educational_keywords({edu_count})")
        
        # Question-based content
        question_count = sum(1 for keyword in self.question_indicators if keyword in text)
        if question_count > 0:
            score += question_count * 1.0
            features.append(f"question_indicators({question_count})")
        
        # Urgency indicators
        urgency_words = ['now', 'today', 'urgent', 'breaking', 'live', 'happening']
        urgency_count = sum(1 for word in urgency_words if word in text)
        if urgency_count > 0:
            score += urgency_count * 0.8
            features.append(f"urgency({urgency_count})")
        
        # Emotional indicators
        emotion_words = ['love', 'hate', 'amazing', 'terrible', 'incredible', 'shocking']
        emotion_count = sum(1 for word in emotion_words if word in text)
        if emotion_count > 0:
            score += emotion_count * 0.6
            features.append(f"emotion({emotion_count})")
        
        # Text length bonus (but not too long)
        text_length = len(text.split())
        if 10 <= text_length <= 50:  # Sweet spot for engagement
            score += 0.5
            features.append("optimal_length")
        elif text_length > 100:
            score -= 0.3  # Penalty for very long text
            features.append("too_long")
        
        # Exclamation marks (excitement)
        exclamation_count = transcript.count('!')
        if exclamation_count > 0:
            score += min(exclamation_count * 0.2, 1.0)  # Cap bonus
            features.append(f"exclamations({exclamation_count})")
        
        # Metadata-based adjustments
        if metadata:
            # View count boost
            view_count = metadata.get('view_count', 0)
            if view_count > 100000:  # 100k+ views
                score += 1.0
                features.append("high_views")
            elif view_count > 10000:  # 10k+ views
                score += 0.5
                features.append("medium_views")
            
            # Live stream bonus
            if metadata.get('is_live'):
                score += 0.8
                features.append("live_stream")
        
        # Normalize score to 0-10 range
        normalized_score = min(max(score, 0), 10)
        
        return {
            'engagement_score': normalized_score,
            'confidence': 0.7,  # Reasonable confidence for keyword-based
            'method': 'keyword_based',
            'features': features,
            'raw_score': score
        }
    
    @expose
    async def predict_batch_engagement(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Predict engagement for multiple segments"""
        results = []
        
        for segment in segments:
            text = segment.get('text', '')
            metadata = segment.get('metadata', {})
            
            # Add segment-specific metadata
            segment_metadata = {
                'duration': segment.get('end', 0) - segment.get('start', 0),
                'start_time': segment.get('start', 0),
                'confidence': segment.get('avg_logprob', -1.0)
            }
            segment_metadata.update(metadata)
            
            prediction = await self.predict_engagement(text, segment_metadata)
            
            # Add segment info to prediction
            prediction.update({
                'segment_start': segment.get('start', 0),
                'segment_end': segment.get('end', 0),
                'segment_text': text
            })
            
            results.append(prediction)
        
        return results
    
    @expose
    async def get_top_segments(self, segments: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
        """Get top N most engaging segments"""
        # Predict engagement for all segments
        predictions = await self.predict_batch_engagement(segments)
        
        # Sort by engagement score
        sorted_predictions = sorted(
            predictions,
            key=lambda x: x['engagement_score'],
            reverse=True
        )
        
        return sorted_predictions[:top_n]
    
    @expose
    async def get_status(self):
        """Get predictor status"""
        return {
            "running": self.running,
            "models_loaded": self.models_loaded,
            "use_ai_scoring": self.use_engagement_scoring,
            "confidence_threshold": self.confidence_threshold,
            "high_engagement_keywords": len(self.high_engagement_keywords),
            "educational_keywords": len(self.educational_keywords)
        }
    
    @expose
    async def update_keywords(self, high_engagement: List[str] = None, educational: List[str] = None):
        """Update keyword lists"""
        if high_engagement:
            self.high_engagement_keywords = list(set(self.high_engagement_keywords + high_engagement))
        
        if educational:
            self.educational_keywords = list(set(self.educational_keywords + educational))
        
        logger.info("Engagement keywords updated")
        return await self.get_status()