from qwen_agent.prompts.retrieval_qa import RetrievalQA


class Summarize(RetrievalQA):
    # TODO: This kwargs is just for fixing the signature warning. Any better way?
    def _run(self, ref_doc, lang: str = 'en', **kwargs):
        assert len(kwargs) == 0
        if lang == 'zh':
            user_request = '总结参考资料的主要内容'
        elif lang == 'en':
            user_request = 'Summarize the main content of reference materials.'
        else:
            raise NotImplementedError
        return super()._run(user_request=user_request,
                            ref_doc=ref_doc,
                            lang=lang)
