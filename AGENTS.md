This project uses pixi to manage its environment.

look at the pyproject.toml to see the pixi tasks

Workflow:
    * On first message:
        - create a new specification according to the pattern specs/01/short-spec-name/spec.md.  Keep it as concise as possible
        - create a plan in the same folder, you can expand more here
        - commit the contents of this folder only

    * Every time I ask for a change
        - update the spec.md with clarifications while keeping it concise. commit if there are changes
        - implement the change
        - run `pixi run ci`
        - fix errors and iterate until ci passes
        - only if ci passes commit the changes.