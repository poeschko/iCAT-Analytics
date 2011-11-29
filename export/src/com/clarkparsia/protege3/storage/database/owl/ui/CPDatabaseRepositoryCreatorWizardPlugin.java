package com.clarkparsia.protege3.storage.database.owl.ui;

import java.util.logging.Logger;


import edu.stanford.smi.protege.util.Log;
import edu.stanford.smi.protege.util.WizardPage;
import edu.stanford.smi.protegex.owl.model.OWLModel;
import edu.stanford.smi.protegex.owl.ui.repository.wizard.RepositoryCreatorWizardPanel;
import edu.stanford.smi.protegex.owl.ui.repository.wizard.RepositoryCreatorWizardPlugin;


public class CPDatabaseRepositoryCreatorWizardPlugin implements
        RepositoryCreatorWizardPlugin {
    static transient final Logger log = Log.getLogger(CPDatabaseRepositoryCreatorWizardPlugin.class);
    
    public String getName() {
        return "Clark-Parsia Database Repository";
    }
    
    public String getDescription() {
        return "Create a repository representing ontologies found in a Clark-Parsia database";
    }
    
    public boolean isSuitable(OWLModel model) {
        return true;
    }

    public RepositoryCreatorWizardPanel createRepositoryCreatorWizardPanel(WizardPage wizardPage,
                                                                           OWLModel owlModel) {
        return new CPDatabaseWizardPanel(wizardPage, owlModel);
    }

}
