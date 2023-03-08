import subprocess
import os
from datetime import datetime

FILTERED_REMOTE_BRANCHES = "REMOTE_branches_to_delete.txt"
FILTERED_LOCAL_BRANCHES = "LOCAL_branches_to_delete.txt"
FAILED_BRANCHES = "branch_failed_to_delete.txt"
SUCCESSFULLY_DELETED_BRANCHES = "branches_successfully_deleted.txt"


class BranchCleaner:
    def __init__(self, branch_names_to_match=[], start_date=None, end_date=None, is_remote=False):
        # read from command line input
        self.branch_names_to_match = branch_names_to_match
        self.start_date = start_date
        self.end_date = end_date
        self.is_remote = is_remote
        # fixed values, customize base on need
        self.debug = True
        self.base_branch = "main"  # root branch, usually 'master' or 'main'
        self.protected_branches = [
            "origin/master/", "origin/main/", "origin/release/", "origin/feature/"]  # branches that are forbidden to delete
        # program used values
        self.branches = []
        self.merged_branches = []
        self.filtered_branches = []

    def run_filter_branches(self):
        # determine command to run
        ls_all_branch_command = []
        ls_merge_branch_command = []
        if self.is_remote:
            ls_all_branch_command = ["git", "branch", "-r"]
            ls_merge_branch_command = ["git", "branch",
                                       "-r", "--merged", self.base_branch]
        else:
            ls_all_branch_command = ["git", "branch", "-l"]
            ls_merge_branch_command = ["git", "branch",
                                       "-l", "--merged", self.base_branch]

        # get remote/local branches
        all_branches = subprocess.run(ls_all_branch_command, capture_output=True,
                                      text=True).stdout.strip().split("\n")
        self.branches = [branch.strip() for branch in all_branches if
                         len([prefix for prefix in self.protected_branches if prefix in branch]) == 0]

        # get merged remote/local branches
        all_merged_branches = subprocess.run(ls_merge_branch_command, capture_output=True,
                                             text=True).stdout.splitlines()
        self.merged_branches = [branch.strip() for branch in all_merged_branches if
                                len([prefix for prefix in self.protected_branches if prefix in branch]) == 0]

        # filter logic
        for branch in self.branches:
            branch_last_commit_date = self.__get_last_commit_date(branch)

            if self.debug:
                print("Branch name: {}, Last Commit Date: {}".format(
                    branch, branch_last_commit_date))

            # branch not within the provided date, if any
            if self.start_date is not None and self.end_date is not None and not self.__check_branch_date_match(
                    branch_last_commit_date):
                if self.debug:
                    print(
                        "Branch last commit date {} not within {} - {}".format(branch_last_commit_date, self.start_date,
                                                                               self.end_date))
                continue

            # branch is not merged
            # NOTE: if merged_branches is 0, then can still delete remote branches that are not merged. But this will only happen if the repo has 0 merged branches
            if len(self.merged_branches) > 0 and not self.__check_branch_name_match(self.merged_branches, branch):
                if self.debug:
                    print(
                        "Branch {} does not match patterns in merged branches {}".format(branch, self.merged_branches))
                continue

            # branch name does not match any of the provided branch names
            if len(self.branch_names_to_match) > 0 and not self.__check_branch_name_match(self.branch_names_to_match,
                                                                                          branch):
                if self.debug:
                    print("Branch {} does not match patterns in provided names {}".format(branch,
                                                                                          self.branch_names_to_match))
                continue

            self.filtered_branches.append(branch)

        self.__output_branch_to_file()

    # delete filtered branches specified in FILTERED_REMOTE_BRANCHES or FILTERED_LOCAL_BRANCHES
    # append successfully deleted branches in SUCCESSFULLY_DELETED_BRANCHES
    # append failed to delete branches in FAILED_BRANCHES
    def run_delete_filtered_branches(self):
        # track which branches have been successfully deleted and failed to delete
        failed_branches = []
        successfully_deleted_branches = []
        root_command = []
        file_to_read = None

        if os.path.isfile(FILTERED_REMOTE_BRANCHES):
            file_to_read = FILTERED_REMOTE_BRANCHES
            root_command = ["git", "push", "origin", "--delete"]
        elif os.path.isfile(FILTERED_LOCAL_BRANCHES):
            file_to_read = FILTERED_LOCAL_BRANCHES
            root_command = ["git", "branch", "-D"]
        else:
            print("No {} or {} files are found!".format(
                FILTERED_LOCAL_BRANCHES, FILTERED_REMOTE_BRANCHES))
            return

        with open(file_to_read, "r") as f:
            for branch in f:
                branch = branch.strip().replace("origin/", "")
                del_command = root_command.copy()
                del_command.append(branch)

                output = subprocess.run(
                    del_command, capture_output=True, text=True).stderr.lower()

                if "deleted" in output:
                    if self.debug:
                        print("Branch {} deleted!".format(branch))

                    successfully_deleted_branches.append(branch)
                elif "failed" in output:
                    if self.debug:
                        print("Delete branch {} failed!".format(branch))

                    failed_branches.append(branch)

        os.remove(file_to_read)

        if len(successfully_deleted_branches) > 0:
            with open(SUCCESSFULLY_DELETED_BRANCHES, 'a') as file:
                file.writelines(
                    "%s" % branch for branch in successfully_deleted_branches)

        if len(failed_branches) > 0:
            with open(FAILED_BRANCHES, 'a') as file:
                file.writelines("%s" % branch for branch in failed_branches)

            print("Some branches failed to delete. Please check {}".format(
                FAILED_BRANCHES))

    # get the last commit date of the branch
    # the last commit date is used for filtering
    def __get_last_commit_date(self, branch):
        date_string = subprocess.run(["git", "log", "-1", "--format=%ci", branch], capture_output=True,
                                     text=True).stdout.strip()

        return datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S %z").replace(tzinfo=None) if date_string else None

    # returns True if the branch name matches of the names in the list of names to check
    # if list is not provided, return False
    def __check_branch_name_match(self, list_to_check, branch_name):
        for pattern in list_to_check:
            if pattern in branch_name or branch_name in pattern:
                return True

        return False

    # returns True if the branch last commit date matches the provided date range
    # if date range is not provided, return False
    def __check_branch_date_match(self, branch_date):
        if branch_date:
            return self.start_date <= branch_date <= self.end_date

        return False

    # output filtered branches into the corresponding file for subsequent deletion
    def __output_branch_to_file(self):
        if os.path.isfile(FILTERED_REMOTE_BRANCHES):
            os.remove(FILTERED_REMOTE_BRANCHES)
            print(f"Old {FILTERED_REMOTE_BRANCHES} was deleted")

        if os.path.isfile(FILTERED_LOCAL_BRANCHES):
            os.remove(FILTERED_LOCAL_BRANCHES)
            print(f"Old {FILTERED_LOCAL_BRANCHES} was deleted")

        if len(self.filtered_branches) == 0:
            print("No branches flagged for deletion")
            return

        file_to_write = FILTERED_REMOTE_BRANCHES if self.is_remote else FILTERED_LOCAL_BRANCHES

        with open(file_to_write, 'w') as file:
            file.writelines("%s\n" %
                            branch for branch in self.filtered_branches)

            print("Please confirm you want to delete {} branches in {} \n".format(
                "REMOTE" if self.is_remote else "LOCAL", file_to_write))

        for branch in self.filtered_branches:
            print(branch)


# Program Main Entry Point
if __name__ == "__main__":

    # STEP 1: Filter branches to delete
    def run_filter_branches(is_remote=True):
        # get name
        parsed_branch_names = []
        branch_names = input(
            "Enter branch names to delete in the following format: branch1 branch2 branch3\n")

        if len(branch_names) > 0:
            parsed_branch_names = branch_names.split(" ")
        else:
            print("No branch names to filter\n")

        # get date
        start_date = input(
            "Enter start date to filter in the following format: 2023-01-27 14:35:00\n")

        if len(start_date) > 0:
            start_date = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
        else:
            print("No date to filter\n")
            start_date = None

        end_date = None
        if start_date:
            end_date = input(
                "Enter end date to filter in the following format: 2023-01-27 14:35:00\n")
            if len(end_date) > 0:
                end_date = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
            else:
                raise Exception(
                    "No end date to filter when start date is provided\n")

        branch_filter = BranchCleaner(
            parsed_branch_names, start_date, end_date, is_remote)
        branch_filter.run_filter_branches()

    # STEP 2: delete filtered branches
    def run_delete_filtered_branches():
        # check if required files exist
        if not os.path.isfile(FILTERED_REMOTE_BRANCHES) and not os.path.isfile(FILTERED_LOCAL_BRANCHES):
            print("File {} and {} do not exist, please filter first!".format(
                FILTERED_REMOTE_BRANCHES, FILTERED_LOCAL_BRANCHES))
            return

        # cannot have both local and remote files
        if os.path.isfile(FILTERED_REMOTE_BRANCHES) and os.path.isfile(FILTERED_LOCAL_BRANCHES):
            print("Only can delete either {} or {}, not both!".format(
                FILTERED_REMOTE_BRANCHES, FILTERED_LOCAL_BRANCHES))
            return

        option = input(
            "\nEnter y to delete {} branches: ".format("LOCAL" if os.path.isfile(FILTERED_LOCAL_BRANCHES) else "REMOTE"))

        if option.lower() == "y":
            branch_cleaner = BranchCleaner()
            branch_cleaner.run_delete_filtered_branches()
        else:
            print("Please enter Y, exiting...")

    # program entry point
    while True:
        option = int(input(
            "Select option:\n    (1) Filter branches to delete\n    (2) Delete filtered branches\n"))

        if option == 1:
            remote_or_local_option = int(input(
                "Select option:\n    (1) Filter REMOTE branches to delete\n    (2) Filter LOCAL branches to delete\n"))

            if remote_or_local_option == 1:
                run_filter_branches(True)
            elif remote_or_local_option == 2:
                run_filter_branches(False)
            else:
                print("Invalid selection, try again.")

            break
        elif option == 2:
            run_delete_filtered_branches()
            break
        else:
            print("Invalid selection, try again.")
